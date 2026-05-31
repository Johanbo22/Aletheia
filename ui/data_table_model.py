import pandas as pd
import numpy as np
import operator
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from PyQt6.QtGui import QColor, QFont
from typing import Any
from ui.status_bar import StatusBar
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.data_handler import DataHandler

class DataTableModel(QAbstractTableModel):
    """ table for the data Table"""

    def __init__(self, data_handler: "DataHandler", editable: bool=False, parent: Any=None, highlighted_rows: list[int] | None=None, float_precision: int = 2, conditional_rules: list[dict[str, Any]] | None = None):
        super().__init__(parent)
        self.data_handler = data_handler
        self._data = self.data_handler.df
        self.editable = editable
        self.highlighted_rows = set(highlighted_rows) if highlighted_rows else set()
        self.float_precision = float_precision
        self.conditional_rules = conditional_rules if conditional_rules else []
        self.render_bools_as_checkboxes = True
        self.nan_display = "NaN"
        self.thousands_separator = False
        self.scientific_notation = False
        self._compiled_rules: list[tuple] = []
        self._compile_rules(self.conditional_rules)
        
        self._highlight_color = QColor("#ffcccc")
        self._nan_color = QColor("#a0a0a0")
        self._nan_font = QFont()
        self._nan_font.setItalic(True)
        
        self._col_alignments: list[Qt.AlignmentFlag] = []
        self._col_is_bool: list[bool] = []
        self._header_tooltips: list[str] = []

        if self._data is not None:
            self._is_numeric = [
                pd.api.types.is_numeric_dtype(dtype) for dtype in self._data.dtypes
            ]
    
    def set_float_precision(self, precision: int):
        """Updates the floating point precision and refreshes the datble"""
        self.float_precision = precision
        self.layoutChanged.emit()
    
    def set_bool_render_style(self, as_checkboxes: bool) -> None:
        """Updates how boolean values are rendered (checkboxes vs text) and refreshes the table"""
        self.render_bools_as_checkboxes = as_checkboxes
        self.layoutChanged.emit()

    def set_nan_display(self, text: str) -> None:
        """Updates the display text for missing values"""
        self.nan_display = text
        self.layoutChanged.emit()

    def set_thousands_separator(self, use_sep: bool) -> None:
        """Toggles the thousand separator for numerical formatting"""
        self.thousands_separator = use_sep
        self.layoutChanged.emit()

    def set_scientific_notation(self, use_sci: bool) -> None:
        """Toggles scientific notation for numerical formatting"""
        self.scientific_notation = use_sci
        self.layoutChanged.emit()
    
    def set_conditional_rules(self, rules: list):
        """Updates the conditional formatting rules and refreshes the dtable"""
        self.conditional_rules = rules
        self._compile_rules(rules)
        self.layoutChanged.emit()
    
    def _compile_rules(self, rules: list) -> None:
        """Pre-compiles conditional rules to eliminate dict lookups and string parsing from the render loop"""
        self._compiled_rules.clear()
        op_map = {
            "<": operator.lt,
            ">": operator.gt,
            "=": operator.eq,
            "<=": operator.le,
            ">=": operator.ge
        }
        for rule in rules:
            op_str: str = rule.get("operator", "")
            target: float = rule.get("value", 0.0)
            color_hex: str = rule.get("color", "#000000")
            
            op_func = op_map.get(op_str)
            if op_func:
                self._compiled_rules.append((op_func, target, QColor(color_hex)))
    
    def set_highlighted_rows(self, rows: set) -> None:
        """Updates the highlighed rows and triggers a layout refresh on display changes"""
        self.highlighted_rows = set(rows) if rows else set()
        self.layoutChanged.emit()
        
    def _update_column_alignments(self) -> None:
        """Pre-computes and caches the Qt Alignment flags for each column based on its dtype"""
        if not hasattr(self, '_col_alignments'): 
            self._col_alignments = []
        else: 
            self._col_alignments.clear()
        if not hasattr(self, '_col_is_bool'): 
            self._col_is_bool = []
        else: 
            self._col_is_bool.clear()
        if not hasattr(self, '_header_tooltips'): 
            self._header_tooltips = []
        else: 
            self._header_tooltips.clear()
            
        if self._data is None:
            return
            
        align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        align_left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        for i in range(len(self._data.columns)):
            try:
                dtype = self._data.dtypes.iloc[i]
                col_name = str(self._data.columns[i])
            except Exception:
                dtype = "unknown"
                col_name = f"Column {i}"
                
            try:
                if pd.api.types.is_numeric_dtype(dtype):
                    self._col_alignments.append(align_right)
                else:
                    self._col_alignments.append(align_left)
            except Exception:
                self._col_alignments.append(align_left)
                
            try:
                self._col_is_bool.append(self._infer_boolean_column(i))
            except Exception:
                self._col_is_bool.append(False)
            
            try:
                missing_count = int(self._data.iloc[:, i].isna().sum())
                self._header_tooltips.append(f"Column: {col_name}\nType: {dtype}\nMissing Values: {missing_count:,}")
            except Exception:
                self._header_tooltips.append(f"Column: {col_name}\nType: {dtype}")
    
    def _infer_boolean_column(self, col_idx: int) -> bool:
        """Infers if a column represents booleans, even if stored as strings or integers"""
        dtype = self._data.dtypes.iloc[col_idx]
        
        if pd.api.types.is_bool_dtype(dtype):
            return True
        
        if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
            series = self._data.iloc[:, col_idx].dropna()
            if series.empty:
                return False
            
            uniques = series.unique()
            valid_text_bools = {"true", "false", "t", "f", "yes", "no"}
            
            for val in uniques:
                if isinstance(val, bool):
                    continue
                if isinstance(val, str):
                    if val.strip().lower() not in valid_text_bools:
                        return False
                elif isinstance(val, (int, float)):
                    if val not in (0, 1, 0.0, 1.0):
                        return False
                else:
                    return False
            return True
        
        if pd.api.types.is_integer_dtype(dtype):
            series = self._data.iloc[:, col_idx].dropna()
            if series.empty:
                return False
            uniques = series.unique()
            for val in uniques:
                if val not in (0, 1):
                    return False
            return True
            
        return False
    
    def update_data(self) -> None:
        self.beginResetModel()
        self._data = self.data_handler.df
        self.highlighted_rows.clear()
        self._update_column_alignments()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Returns the number of rows in a dataframe"""
        if parent.isValid() or self._data is None:
            return 0
        base_count: int = self._data.shape[0]
        return base_count + 1 if self.editable else base_count
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Returns the number of columns in the dataframe"""
        if parent.isValid() or self._data is None:
            return 0
        base_count: int = self._data.shape[1]
        return base_count + 1 if self.editable else base_count
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Returns le data"""
        if not index.isValid() or self._data is None:
            return None
    
        _supported_roles = (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.BackgroundRole,
            Qt.ItemDataRole.TextAlignmentRole,
            Qt.ItemDataRole.ToolTipRole,
            Qt.ItemDataRole.EditRole,
            Qt.ItemDataRole.ForegroundRole,
            Qt.ItemDataRole.FontRole,
            Qt.ItemDataRole.CheckStateRole
        )
        if role not in _supported_roles:
            return None
        
        row: int = index.row()
        col: int = index.column()
        
        is_insert_row: bool = self.editable and row == self._data.shape[0]
        is_insert_col: bool = self.editable and col == self._data.shape[1]
        
        if is_insert_row and is_insert_col:
            if role == Qt.ItemDataRole.BackgroundRole:
                return QColor("#f8f9fa")
            return None
        
        if role == Qt.ItemDataRole.BackgroundRole:
            if row in self.highlighted_rows:
                return self._highlight_color
            return None
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if self._col_alignments and 0 <= col < len(self._col_alignments):
                return self._col_alignments[col]
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        try:
            val: Any = self._data.iat[row, col]
        except Exception as error:
            return None
            
        is_missing = pd.api.types.is_scalar(val) and pd.isna(val)
        # Skip retrieval if there are no conditional formatting set
        if role == Qt.ItemDataRole.ForegroundRole and not self._compiled_rules:
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_data(val, col, is_missing)
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._get_tooltip_data(val)
        if role == Qt.ItemDataRole.EditRole:
            return self._get_edit_data(val)
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._get_foreground_data(val, is_missing)
        if role == Qt.ItemDataRole.FontRole:
            return self._get_font_data(is_missing)
        if role == Qt.ItemDataRole.CheckStateRole:
            return self._get_check_state_data(val, col, is_missing)
        
        return None
    
    def _get_display_data(self, val: Any, col: int, is_missing: bool = False) -> Any:
        """Formats and returns the data for the DisplayRole"""
        try:
            if is_missing:
                return "" if self.nan_display == "<Empty>" else self.nan_display

            # Suppress text rendering entirely for inferred Checkbox columns if setting is enabled
            if self.render_bools_as_checkboxes and self._col_is_bool and 0 <= col < len(self._col_is_bool) and \
                    self._col_is_bool[col]:
                return ""

            if isinstance(val, float) or isinstance(val, np.floating):
                if np.isnan(val):
                    return "" if self.nan_display == "<Empty>" else self.nan_display

                if self.scientific_notation:
                    return f"{val:.{self.float_precision}e}"
                elif self.thousands_separator:
                    return f"{val:,.{self.float_precision}f}"
                else:
                    return f"{val:.{self.float_precision}f}"

            if not self.render_bools_as_checkboxes and self._col_is_bool and 0 <= col < len(self._col_is_bool) and \
                    self._col_is_bool[col]:
                return str(self._parse_bool(val))
            if isinstance(val, pd.Timestamp):
                return val.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(val, (int, np.integer)):
                if self.scientific_notation:
                    return f"{val:.{self.float_precision}e}"
                elif self.thousands_separator:
                    return f"{val:,}"
                return str(val)

            s_val: str = str(val)
            CHARACTER_LIMIT: int = 64
            if len(s_val) > CHARACTER_LIMIT:
                return s_val[:CHARACTER_LIMIT] + "..."
            return s_val

        except Exception:
            return None
        
    def _get_tooltip_data(self, val: Any) -> str | None:
        """Formats and returns data for the ToolTipRole for long strings"""
        try:
            CHARACTER_LIMIT: int = 64
            if isinstance(val, str) and len(val) > CHARACTER_LIMIT:
                return val
        except Exception as error:
            print(error)
        return None
    
    def _get_edit_data(self, val: Any, is_missing: bool = False) -> str:
        """Formats and returns data tailored for the EditRole"""
        try:
            if is_missing:
                return ""
            if isinstance(val, pd.Timestamp):
                return val.strftime("%Y-%m-%d %H:%M:%S")
            return str(val)
        except Exception:
            return ""
    
    def _get_foreground_data(self, val: Any, is_missing: bool = False) -> QColor | None:
        """Evaluates conditional rules and returns the QColor for ForegroundRole"""
        try:
            if is_missing:
                return self._nan_color
            if isinstance(val, (int, float, np.number)):
                for op_func, target, color in self._compiled_rules:
                    if op_func(val, target):
                        return color
        except Exception as error:
            print(error)
        return None
    
    def _get_font_data(self, is_missing: bool = False) -> QFont | None:
        """Applies italics to missing data to distinctively demote it"""
        if is_missing:
            return self._nan_font
        return None
    
    def _parse_bool(self, val: Any) -> bool:
        """Safely extracts boolean state from mixed data types"""
        if isinstance(val, bool) or isinstance(val, np.bool_):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"true", "t", "yes", "1"}
        if isinstance(val, (int, float, np.number)):
            return bool(val)
        return False
    
    def _get_check_state_data(self, val: Any, col: int, is_missing: bool = False) -> int | None:
        """Renders actual checkboxes for boolean columns"""
        if not self.render_bools_as_checkboxes:
            return None
        
        if self._col_is_bool and 0 <= col < len(self._col_is_bool):
            if self._col_is_bool[col] and not is_missing:
                is_checked = self._parse_bool(val)
                return Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """data ypdater"""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole or not self.editable:
            return False
        
        if role == Qt.ItemDataRole.CheckStateRole:
            value = bool(value == Qt.CheckState.Checked.value)
        elif role != Qt.ItemDataRole.EditRole:
            return False
        
        try:
            row = index.row()
            column = index.column()
            
            self.data_handler.update_cell(row, column, value)

            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.CheckStateRole])
            return True
        
        except Exception as UpdateDataModelError:
            print(f"Error updating data: {str(UpdateDataModelError)}")
            return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags"""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        row: int = index.row()
        col: int = index.column()
        
        is_insert_row: bool = self.editable and self._data is not None and row == self._data.shape[0]
        is_insert_col: bool = self.editable and self._data is not None and col == self._data.shape[1]
        
        if is_insert_row or is_insert_col:
            return Qt.ItemFlag.NoItemFlags
        
        default_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        if self.render_bools_as_checkboxes and self._col_is_bool and 0 <= col < len(self._col_is_bool):
            if self._col_is_bool[col]:
                default_flags |= Qt.ItemFlag.ItemIsUserCheckable

        if self.editable:
            return default_flags | Qt.ItemFlag.ItemIsEditable
        
        return default_flags
    
    def set_editable(self, editable: bool) -> None:
        """Update the editable state of the table model"""
        if self.editable == editable:
            return
        self.layoutAboutToBeChanged.emit()
        self.editable = editable
        self.layoutChanged.emit()
    
    def insert_empty_row(self) -> None:
        """Inserts a new row with NaN values at the end of the DataFrame"""
        if self._data is None:
            return
        
        row_idx: int = self._data.shape[0]
        self.beginInsertRows(QModelIndex(), row_idx, row_idx)
        self.data_handler.df.loc[row_idx] = pd.NA
        self._data = self.data_handler.df
        
        self.endInsertRows()
    
    def insert_empty_column(self) -> None:
        """Append a new column with NaN values ath the of the DF"""
        if self._data is None:
            return
        
        col_idx: int = self._data.shape[1]
        self.beginInsertColumns(QModelIndex(), col_idx, col_idx)
        
        new_col_name: str = f"Column_{col_idx + 1}"
        self.data_handler.df[new_col_name] = pd.NA
        self._data = self.data_handler.df
        
        self._update_column_alignments()
        self.endInsertColumns()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Returns the header of the data"""
        if self._data is None:
            return None
        
        is_display = (role == Qt.ItemDataRole.DisplayRole or role == 0)
        is_tooltip = (role == Qt.ItemDataRole.ToolTipRole or role == 3)
        is_alignment = (role == Qt.ItemDataRole.TextAlignmentRole or role == 7)
        is_font = (role == Qt.ItemDataRole.FontRole or role == 6)
        
        if orientation == Qt.Orientation.Horizontal:
            if self.editable and section == self._data.shape[1]:
                if is_display:
                    return "+"
                elif is_tooltip:
                    return "Add new column"
                elif is_alignment:
                    return Qt.AlignmentFlag.AlignCenter
                elif is_font:
                    handle_font = QFont()
                    handle_font.setBold(True)
                    handle_font.setPointSize(14)
                    return handle_font
                return None
            try:
                if is_display:
                    return str(self._data.columns[section])
                    
                elif is_tooltip:
                    if hasattr(self, '_header_tooltips') and self._header_tooltips and 0 <= section < len(self._header_tooltips):
                        return self._header_tooltips[section]
                        
                    return f"Column: {self._data.columns[section]}"
                    
                elif is_alignment:
                    if self._col_alignments and 0 <= section < len(self._col_alignments):
                        return self._col_alignments[section]
                        
            except Exception:
                pass
                
        elif orientation == Qt.Orientation.Vertical:
            if self.editable and section == self._data.shape[0]:
                if is_display:
                    return "+"
                elif is_tooltip:
                    return "Add new row"
                elif is_alignment:
                    return Qt.AlignmentFlag.AlignCenter
                elif is_font:
                    handle_font = QFont()
                    handle_font.setBold(True)
                    handle_font.setPointSize(14)
                    return handle_font
                return None
            if is_display:
                try:
                    return str(self._data.index[section])
                except IndexError:
                    pass
        
        return None
    
    def sort(self, column: int, order: Qt.SortOrder) -> None:
        """Sorts the dataframe based on the given column and the given order"""
        if self._data is None:
            return
        
        # Validate column index to prevent error on empty dataframe
        # Suppresses sorting errors for index -1 is out of bounds when 
        # creating a new project with 0x0 row/cols
        if column < 0 or column >= len(self._data.columns):
            return
        
        self.layoutAboutToBeChanged.emit()

        try:
            col_name = self._data.columns[column]
            ascending = (order == Qt.SortOrder.AscendingOrder)

            self.data_handler.sort_data(col_name, ascending)
            self._data = self.data_handler.df
            self._update_column_alignments()
        except Exception as SortError:
            print(f"Error sorting data: {str(SortError)}")
            self.status_bar = StatusBar()
            self.status_bar.log(f"Error sorting data: {str(SortError)}")
        
        self.layoutChanged.emit()