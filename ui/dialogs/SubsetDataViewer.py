from PyQt6.QtWidgets import QDialog, QFileDialog, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton

class SubsetDataViewer(QDialog):
    """View data in a subset"""

    def __init__(self, df, subset_name, parent=None):
        super().__init__(parent)
        self.df = df
        self.setWindowTitle(f"Subset Data: {subset_name}")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Info
        info = QLabel(f"Showing {len(df):,} rows x {len(df.columns)} columns")
        info.setObjectName("susbet_info_label")
        layout.addWidget(info)

        # Table
        table = QTableWidget()
        table.horizontalHeader().setObjectName("MainDataHeader")
        table.verticalHeader().setObjectName("MainDataHeader")
        table.setAlternatingRowColors(True)
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns.tolist())

        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = df.iloc[row, col]
                item = QTableWidgetItem(str(value))
                table.setItem(row, col, item)

        table.resizeColumnsToContents()

        layout.addWidget(table)

        #export btn
        export_btn = QPushButton("Export this subset", parent=self)
        export_btn.clicked.connect(self.export_subset)
        layout.addWidget(export_btn)

        #close btn
        close_btn = QPushButton("Close", parent=self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def export_subset(self):
        """Export the subset data into a file"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Subset Data",
            "subset_data.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
        )

        if filepath:
            try:
                if filepath.endswith(".csv"):
                    self.df.to_csv(filepath, index=False)
                elif filepath.endswith(".xlsx"):
                    self.df.to_excel(filepath, index=False)
                elif filepath.endswith(".json"):
                    self.df.to_json(filepath)

                QMessageBox.information(self, "Success", f"Subset exported to:\n{filepath}")
            except Exception as ExportSubsetError:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(ExportSubsetError)}")