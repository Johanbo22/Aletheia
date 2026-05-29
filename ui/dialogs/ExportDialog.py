from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QButtonGroup, QAbstractItemView, QListWidgetItem, QMessageBox, QApplication, QWidget, QFrame, QRadioButton, QListWidget, QLineEdit, QGroupBox, QComboBox, QCheckBox, QPushButton
from PyQt6.QtCore import Qt, QTimer
import pandas as pd
from typing import Optional, List, Any, Dict
from pathlib import Path

from core.data_handler import DataHandler
from ui.theme import ThemeColors
from ui.icons import IconBuilder, IconType

class ExportDialog(QDialog):
    """Dialog for exporting data"""

    def __init__(self, parent: Optional[QWidget] = None, data_handler=None, selected_rows=None, selected_columns=None):
        super().__init__(parent)
        self.setWindowTitle("Export Data to file")
        self.setWindowIcon(IconBuilder.build(IconType.ExportFle))
        self.setModal(True)
        self.resize(700, 600)

        self.data_handler: DataHandler = data_handler
        self.selected_rows: List[int] = selected_rows if selected_rows is not None else []
        self.pre_selected_columns: List[str] = selected_columns if selected_columns is not None else []

        self.has_row_selection: bool = len(self.selected_rows) > 0
        self.has_col_selection: bool = len(self.pre_selected_columns) > 0
        
        self.to_clipboard: bool = False
        self.filepath: Optional[str] = None

        self.available_columns = []
        if self.data_handler and self.data_handler.df is not None:
            self.available_columns = list(self.data_handler.df.columns)

        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("&Export Format:")
        format_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        format_layout.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "XLSX", "JSON"])
        self.format_combo.setMinimumWidth(150)
        format_label.setBuddy(self.format_combo)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Data selection layout
        selection_group = QGroupBox("Data Selection", parent=self)
        selection_layout = QVBoxLayout()
        selection_layout.setContentsMargins(15, 20, 15, 15)
        selection_layout.setSpacing(12)
        
        rows_label = QLabel("Rows:")
        rows_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        selection_layout.addWidget(rows_label)
        
        rows_radio_layout = QHBoxLayout()
        self.rows_group = QButtonGroup(self)
        
        self.rows_radio_all = QRadioButton("All Rows")
        self.rows_radio_all.setChecked(True)
        self.rows_group.addButton(self.rows_radio_all)
        rows_radio_layout.addWidget(self.rows_radio_all)
        
        self.rows_radio_selected = QRadioButton(f"Selected Rows Only: {len(self.selected_rows)}")
        self.rows_group.addButton(self.rows_radio_selected)
        rows_radio_layout.addWidget(self.rows_radio_selected)
        rows_radio_layout.addStretch()

        if self.has_row_selection:
            self.rows_radio_selected.setChecked(True)
        else:
            self.rows_radio_all.setChecked(True)
            self.rows_radio_selected.setEnabled(False)
            self.rows_radio_selected.setToolTip("No rows selected in the table")
        
        selection_layout.addLayout(rows_radio_layout)
        
        inner_separator = QFrame()
        inner_separator.setFrameShape(QFrame.Shape.HLine)
        inner_separator.setFrameShadow(QFrame.Shadow.Sunken)
        inner_separator.setProperty("styleClass", "dialog_separator")
        selection_layout.addWidget(inner_separator)
        
        cols_label = QLabel("Columns:")
        cols_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        selection_layout.addWidget(cols_label)

        cols_radio_layout = QHBoxLayout()
        self.cols_group = QButtonGroup(self)

        self.cols_radio_all = QRadioButton("All Columns")
        self.cols_radio_all.setChecked(True)
        self.cols_group.addButton(self.cols_radio_all)
        cols_radio_layout.addWidget(self.cols_radio_all)

        self.cols_radio_specific = QRadioButton("Specific Columns")
        self.cols_group.addButton(self.cols_radio_specific)
        cols_radio_layout.addWidget(self.cols_radio_specific)
        cols_radio_layout.addStretch()
        selection_layout.addLayout(cols_radio_layout)
        
        self.column_tools_widget = QWidget()
        column_tools_layout = QVBoxLayout(self.column_tools_widget)
        column_tools_layout.setContentsMargins(0, 5, 0, 0)
        column_tools_layout.setSpacing(8)
        
        tools_row_layout = QHBoxLayout()
        self.column_filter_input = QLineEdit()
        self.column_filter_input.setPlaceholderText("Filter columns...")
        self.column_filter_input.setClearButtonEnabled(True)
        
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(250)
        self.filter_timer.timeout.connect(self._filter_columns)
        
        self.column_filter_input.textChanged.connect(self._apply_column_filter)
        tools_row_layout.addWidget(self.column_filter_input, stretch=1)
        
        self.select_alL_button = QPushButton("Select all", parent=self)
        self.select_alL_button.clicked.connect(self._select_all_columns)
        tools_row_layout.addWidget(self.select_alL_button)

        self.clear_selection_button = QPushButton("Clear", parent=self)
        self.clear_selection_button.clicked.connect(self._clear_column_selection)
        tools_row_layout.addWidget(self.clear_selection_button)
        
        column_tools_layout.addLayout(tools_row_layout)

        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        column_tools_layout.addWidget(self.column_list)
        
        selection_layout.addWidget(self.column_tools_widget)
        
        if self.available_columns:
            for col in self.available_columns:
                item = QListWidgetItem(col)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                
                if self.has_col_selection and col in self.pre_selected_columns:
                    item.setCheckState(Qt.CheckState.Checked)
                elif not self.has_col_selection:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.column_list.addItem(item)
        else:
            empty_item = QListWidgetItem("No Columns Available")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.column_list.addItem(empty_item)
            self.column_tools_widget.setEnabled(False)
            self.cols_radio_specific.setEnabled(False)
        
        if self.has_col_selection and len(self.pre_selected_columns) < len(self.available_columns):
            self.cols_radio_specific.setChecked(True)
            self.column_tools_widget.setEnabled(True)
        else:
            self.cols_radio_all.setChecked(True)
            self.column_tools_widget.setEnabled(False)
        
        self.cols_radio_all.toggled.connect(self.toggle_column_list)
        self.cols_radio_specific.toggled.connect(self.toggle_column_list)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        options_group = QGroupBox("Options", parent=self)
        options_layout = QVBoxLayout()
        options_layout.setContentsMargins(15, 20, 15, 15)
        options_layout.setSpacing(8)

        self.include_index_check = QCheckBox("Include Index")
        self.include_index_check.setChecked(False)
        options_layout.addWidget(self.include_index_check)

        self.description_label = QLabel()
        self.description_label.setProperty("styleClass", "muted_text")
        self.description_label.setWordWrap(True)
        self.description_label.setMinimumHeight(40)
        options_layout.addWidget(self.description_label)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        
        
        layout.addStretch()
        
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(10)
        
        self.summary_label = QLabel("Calculating Summary...")
        self.summary_label.setProperty("styleClass", "muted_text")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        footer_layout.addWidget(self.summary_label)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setProperty("styleClass", "dialog_separator")
        footer_layout.addWidget(separator)
        
        button_layout = QHBoxLayout()
        
        self.clipboard_button = QPushButton("Copy to clipboard", parent=self)
        self.clipboard_button.setIcon(IconBuilder.build(IconType.Copy))
        self.clipboard_button.setToolTip("Copy the data to system clipboard")
        self.clipboard_button.clicked.connect(self.on_clipboard_clicked)
        button_layout.addWidget(self.clipboard_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.setObjectName("MainActionButton")
        self.export_button.setIcon(IconBuilder.build(IconType.ExportFle))
        self.export_button.setMinimumWidth(100)
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.on_export_clicked)
        button_layout.addWidget(self.export_button)

        self.cancel_button = QPushButton("Cancel", parent=self)
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        footer_layout.addLayout(button_layout)
        layout.addLayout(footer_layout)

        self.setLayout(layout)
        
        self.column_list.itemChanged.connect(self._validate_selection)
        self.cols_radio_all.toggled.connect(self._validate_selection)
        self.cols_radio_specific.toggled.connect(self._validate_selection)
        self.rows_radio_all.toggled.connect(self._validate_selection)
        self.rows_radio_selected.toggled.connect(self._validate_selection)
        self.format_combo.currentTextChanged.connect(self.update_format_info)
        self.include_index_check.stateChanged.connect(self.update_format_info)
        self.update_format_info()
        
        self._validate_selection()
    
    def toggle_column_list(self) -> None:
        """toggle the column list"""
        is_specific = self.cols_radio_specific.isChecked()
        self.column_tools_widget.setEnabled(is_specific)
        if is_specific:
            self.column_filter_input.setFocus()
    
    def _filter_columns(self) -> None:
        self.filter_timer.start()
    
    def _apply_column_filter(self) -> None:
        """
        Hide or show columns in the list based on search text
        """
        search_text = self.column_filter_input.text().lower()
        self.column_list.blockSignals(True)
        for index in range(self.column_list.count()):
            item = self.column_list.item(index)
            if item:
                item_text = item.text().lower()
                item.setHidden(search_text not in item_text)
        self.column_list.blockSignals(False)
    
    def _select_all_columns(self) -> None:
        self.column_list.blockSignals(True)
        for index in range(self.column_list.count()):
            item = self.column_list.item(index)
            if item and not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
        self.column_list.blockSignals(False)
        self._validate_selection()

    def _clear_column_selection(self) -> None:
        self.column_list.blockSignals(True)
        for index in range(self.column_list.count()):
            item = self.column_list.item(index)
            if item and not item.isHidden():
                item.setCheckState(Qt.CheckState.Unchecked)
        self.column_list.blockSignals(False)
        self._validate_selection()
        
    def _validate_selection(self) -> None:
        is_valid: bool = True
        if self.cols_radio_specific.isChecked():
            checked_count = sum(1 for i in range(self.column_list.count()) if self.column_list.item(i).checkState() == Qt.CheckState.Checked)
            if checked_count == 0:
                is_valid = False
        
        self.export_button.setEnabled(is_valid)
        self.clipboard_button.setEnabled(is_valid)
        
        self._update_summary()
    
    def _update_summary(self) -> None:
        if not self.data_handler or self.data_handler.df is None:
            self.summary_label.setText("0 rows x 0 columns")
            return
        
        if self.rows_radio_selected.isChecked() and self.has_row_selection:
            rows = len(self.selected_rows)
        else:
            rows = len(self.data_handler.df)
        
        if self.cols_radio_specific.isChecked():
            cols = sum(1 for i in range(self.column_list.count()) if self.column_list.item(i).checkState() == Qt.CheckState.Checked)
        else:
            cols = len(self.available_columns)
        
        self.summary_label.setText(f"<b>Summary:</b> {rows:,} rows x {cols:,} columns")
        

    def update_format_info(self) -> None:
        """Update a description label based on selected format and current optins"""
        format_selection = self.format_combo.currentText()
        include_index = self.include_index_check.isChecked()
        
        self.export_button.setText(f"Export to {format_selection}...")

        if format_selection == "JSON":
            if include_index:
                self.description_label.setText("Export as a 'columns' oriented JSON.")
            else:
                self.description_label.setText("Export as a 'records' oriented JSON.")
        elif format_selection == "CSV":
            self.description_label.setText("Standard Comma Separated Values file.")
        elif format_selection == "XLSX":
            self.description_label.setText("Microsoft Excel Spreadsheet format.")
        else:
            self.description_label.setText("")
    
    def _get_export_data(self) -> Optional[pd.DataFrame]:
        """Get the dataframe current selection"""
        if not self.data_handler or self.data_handler.df is None:
            return None
        
        df = self.data_handler.df

        if self.rows_radio_selected.isChecked() and self.selected_rows:
            try:
                df = df.iloc[self.selected_rows]
            except IndexError as error:
                QMessageBox.warning(self, "Selection Error", f"Error slicing selected rows. They may be out of bounds.\n{str(error)}")
                return None
            except Exception as error:
                QMessageBox.critical(self, "Slicing Error", f"An unexpected error occurred while filtering rows:\n{str(error)}")
                return None
        
        if self.cols_radio_specific.isChecked():
            selected_cols = [self.column_list.item(i).text() for i in range(self.column_list.count()) if self.column_list.item(i).checkState() == Qt.CheckState.Checked]
            if not selected_cols:
                QMessageBox.warning(self, "No Columns Selected", "Please select at least one column to export.")
                return None
            df = df[selected_cols]
        return df

    def on_clipboard_clicked(self) -> None:
        """Copy to clipboard"""
        self.to_clipboard = True
        if not self.data_handler:
            self.accept()
            return
        
        success: bool = False
        rows: int = 0
        cols: int = 0
        
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            df_to_export = self._get_export_data()
            if df_to_export is not None:
                include_index = self.include_index_check.isChecked()
                df_to_export.to_clipboard(excel=True, index=include_index)
                rows, cols = df_to_export.shape
                success = True
        except Exception as clipboard_error:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to copy to clipboard: {str(clipboard_error)}")
            return
        finally:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        
        if success:
            QMessageBox.information(
                self,
                "Copied",
                f"Copied {rows:,} rows and {cols:,} columns to clipboard\nYou can paste this into Excel or Google Sheets"
            )
            self.accept()

    def on_export_clicked(self) -> None:
        """Handle export button click"""
        export_format = self.format_combo.currentText()

        # Determine file filter and extension
        if export_format == 'CSV':
            file_filter = "CSV Files (*.csv)"
            default_ext = ".csv"
        elif export_format == 'XLSX':
            file_filter = "Excel Files (*.xlsx)"
            default_ext = ".xlsx"
        else:  # JSON
            file_filter = "JSON Files (*.json)"
            default_ext = ".json"

        file_path_string, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            f"export{default_ext}",
            file_filter
        )
        if not file_path_string:
            return
        filepath: Path = Path(file_path_string)
        self.filepath = str(filepath)
        success: bool = False
        
        if not self.data_handler:
            return
        
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            df_to_export = self._get_export_data()
            if df_to_export is not None:
                include_index = self.include_index_check.isChecked()

                if export_format == "CSV":
                    df_to_export.to_csv(filepath, index=include_index)
                elif export_format == "XLSX":
                    df_to_export.to_excel(filepath, index=include_index)
                elif export_format == "JSON":
                    orient = "columns" if include_index else "records"
                    df_to_export.to_json(filepath, orient=orient, indent=4)
                
                success = True
        except Exception as error:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Export Error", f"Failed to export data: {str(error)}")
            return
        finally:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
                
        if success:
            QMessageBox.information(self, "Success", f"Data exported to {filepath.name}")
            self.accept()

    def get_export_config(self) -> Dict[str, Any]:
        """Return export configuration"""
        selected_columns = [self.column_list.item(i).text() for i in range(self.column_list.count()) if self.column_list.item(i).checkState() == Qt.CheckState.Checked]
        
        config = {
            'format': self.format_combo.currentText().lower(),
            'filepath': self.filepath,
            'include_index': self.include_index_check.isChecked(),
            'to_clipboard': self.to_clipboard,
            'selected_rows_only': self.rows_radio_selected.isChecked(),
            'specific_columns': self.cols_radio_specific.isChecked(),
            'selected_columns': selected_columns
        }
        return config