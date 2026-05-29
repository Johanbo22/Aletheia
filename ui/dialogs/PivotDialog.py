from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QSplitter, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QGroupBox, QComboBox, QPushButton
from typing import List, Dict, Any

import pandas as pd
from ui.theme import ThemeColors

class PivotDialog(QDialog):
    """Dialog for performing pivot table operation"""
    
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pivot Table")
        self.setModal(True)
        self.resize(900, 750)
        self.df = df
        self.columns = list(df.columns)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # HEADER_infomation
        info_label = QLabel("Pivot Data")
        info_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        info_description = QLabel(
            "Reshape your data based on columns values.\n"
            "1. Index: Rows to group by.\n"
            "2. Columns: Keys to group by on the columns.\n"
            "3. Values: Column(s) to aggregate by."
        )
        info_description.setProperty("styleClass", "info_text")
        info_description.setWordWrap(True)
        layout.addWidget(info_description)
        
        # A splittter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # index selection
        index_widget = QWidget()
        index_layout = QVBoxLayout(index_widget)
        index_layout.addWidget(QLabel("Index:"))
        self.index_list = QListWidget()
        self.index_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.index_list.addItems(self.columns)
        index_layout.addWidget(self.index_list)
        splitter.addWidget(index_widget)
        
        # colummns selection
        column_widget = QWidget()
        column_layout = QVBoxLayout(column_widget)
        column_layout.addWidget(QLabel("Columns:"))
        self.columns_list = QListWidget()
        self.columns_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.columns_list.addItems(self.columns)
        column_layout.addWidget(self.columns_list)
        splitter.addWidget(column_widget)
        
        # values selection
        values_widget = QWidget()
        values_layout = QVBoxLayout(values_widget)
        values_layout.addWidget(QLabel("Values:"))
        self.values_list = QListWidget()
        self.values_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.values_list.addItems(self.columns)
        values_layout.addWidget(self.values_list)
        splitter.addWidget(values_widget)
        
        layout.addWidget(splitter)
        layout.addSpacing(15)
        
        # Aggregation settings
        agg_group = QGroupBox("Aggregation Settings")
        agg_layout = QHBoxLayout()
        
        agg_layout.addWidget(QLabel("Aggregatation Function:"))
        self.agg_combo = QComboBox()
        self.agg_combo.addItems(["mean", "sum", "count", "min", "max", "median", "std", "var", "first", "last"])
        agg_layout.addWidget(self.agg_combo)
        
        agg_group.setLayout(agg_layout)
        layout.addWidget(agg_group)
        
        # Preview 
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Select parameters and click 'Update Preview'")
        self.preview_label.setObjectName("pivot_preview_label")
        self.preview_label.setProperty("status", "normal")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        self.preview_table = QTableWidget()
        self.preview_table.horizontalHeader().setObjectName("MainDataHeader")
        self.preview_table.verticalHeader().setObjectName("MainDataHeader")
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_table)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        preview_button = QPushButton("Update Preview")
        preview_button.clicked.connect(self.update_preview)
        button_layout.addWidget(preview_button)
        
        apply_button = QPushButton("Pivot Data")
        apply_button.setObjectName("MainActionButton")
        apply_button.setMinimumWidth(120)
        apply_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(apply_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def get_selected_text(self, list_widget: QListWidget) -> List[str]:
        return [item.text() for item in list_widget.selectedItems()]
        
    def update_preview(self):
        """Calculate and display a preview of the pivot operation as a table"""
        index_cols = self.get_selected_text(self.index_list)
        column_col_list = self.get_selected_text(self.columns_list)
        value_cols = self.get_selected_text(self.values_list)
        aggfunc = self.agg_combo.currentText()
        
        if not index_cols:
            self.preview_label.setText("Error: Please select at least one Index column")
            self.preview_label.setProperty("status", "error")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
            return
        
        column_col = column_col_list[0] if column_col_list else None
        
        if not value_cols:
            self.preview_label.setText("Error: Please select at least one Value column")
            self.preview_label.setProperty("status", "error")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
            return
        
        try:
            # To limit data fetching we will use full dataframe to calculate 
            # but limit the display to the first 20 rows
            df_preview_source = self.df.copy()
            
            preview_df = pd.pivot_table(
                df_preview_source,
                index=index_cols,
                columns=column_col,
                values=value_cols,
                aggfunc=aggfunc
            ).reset_index()
            
            if isinstance(preview_df.columns, pd.MultiIndex):
                preview_df.columns = [f"{str(column[0])}_{str(column[1])}" if len(column) > 1 and column[1] else str(column[0]) for column in preview_df.columns]
            
            preview_display = preview_df.head(20)
            
            self.preview_table.clear()
            self.preview_table.setRowCount(preview_display.shape[0])
            self.preview_table.setColumnCount(preview_display.shape[1])
            self.preview_table.setHorizontalHeaderLabels(list(preview_display.columns))
            
            for row in range(preview_display.shape[0]):
                for col in range(preview_display.shape[1]):
                    val = str(preview_display.iat[row, col])
                    self.preview_table.setItem(row, col, QTableWidgetItem(val))
            
            self.preview_label.setText(f"Result Shape: {preview_df.shape} (Showing the first 20 rows)")
            self.preview_label.setProperty("status", "success")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
        
        except Exception as Error:
            self.preview_label.setText(f"Preview error: {str(Error)}")
            self.preview_label.setProperty("status", "error")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
            print(Error)
    
    def validate_and_accept(self):
        index_cols = self.get_selected_text(self.index_list)
        value_cols = self.get_selected_text(self.values_list)
        
        if not index_cols:
            QMessageBox.warning(self, "Validation Error", "Please select at least one Index column")
            return

        if not value_cols:
            QMessageBox.warning(self, "Validation Error", "Please select at least one Value column")
            return
        
        self.accept()
    
    def get_config(self) -> Dict[str, Any]:
        column_col_list = self.get_selected_text(self.columns_list)
        
        return {
            "index": self.get_selected_text(self.index_list),
            "columns": column_col_list[0] if column_col_list else None,
            "values": self.get_selected_text(self.values_list),
            "aggfunc": self.agg_combo.currentText()
        }