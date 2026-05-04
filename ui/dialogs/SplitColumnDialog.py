from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from typing import Optional
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioLineEdit

class SplitColumnDialog(QDialog):
    """Dialog for splitting a string column into new colymns based on a delimiter"""
    def __init__(self, columns: list[str], parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Split Column")
        self.setMinimumWidth(350)
        self.columns: list[str] = columns
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select Column to Split:"))
        self.column_combo = DataPlotStudioComboBox()
        self.column_combo.addItems(self.columns)
        self.column_combo.setToolTip("Select the text column you want to split.")
        layout.addWidget(self.column_combo)

        layout.addWidget(QLabel("Delimiter:"))
        self.delimiter_input = DataPlotStudioLineEdit()
        self.delimiter_input.setText(" ")
        self.delimiter_input.setToolTip("The character(s) separating the values (e.g., a space ' ', comma ',', or dash '-').")
        layout.addWidget(self.delimiter_input)

        layout.addWidget(QLabel("New Column Names (comma-separated):"))
        self.new_columns_input = DataPlotStudioLineEdit()
        self.new_columns_input.setPlaceholderText("e.g., First Name, Last Name")
        self.new_columns_input.setToolTip("Enter the names for the new columns, separated by commas.")
        layout.addWidget(self.new_columns_input)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        self.btn_ok = DataPlotStudioButton("Apply Split", parent=self, base_color_hex=ThemeColors.MainColor)
        self.btn_ok.clicked.connect(self.validate_and_accept)
        
        self.btn_cancel = DataPlotStudioButton("Cancel", parent=self)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
    
    def validate_and_accept(self) -> None:
        if not self.delimiter_input.text():
            QMessageBox.warning(self, "Validation Error", "Please provide a valid delimiter.")
            return
            
        new_cols_raw = self.new_columns_input.text()
        new_cols = [c.strip() for c in new_cols_raw.split(",") if c.strip()]
        
        if len(new_cols) < 2:
            QMessageBox.warning(self, "Validation Error", "Please provide at least two new column names separated by commas.")
            return
            
        self.accept()
    
    def get_parameters(self) -> tuple[str, str, list[str]]:
        """
        Retrieve the configured split parameters.
        Returns:
            tuple: (column_name, delimiter, list_of_new_column_names)
        """
        column: str = self.column_combo.currentText()
        delimiter: str = self.delimiter_input.text()
        new_cols_raw: str = self.new_columns_input.text()
        new_cols: list[str] = [c.strip() for c in new_cols_raw.split(",") if c.strip()]
        
        return column, delimiter, new_cols