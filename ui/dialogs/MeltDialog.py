from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
from typing import List, Tuple, Optional, Dict, Any

import pandas as pd
from core.resource_loader import get_resource_path
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioListWidget


class MeltDialog(QDialog):
    """Dialog for using the melt function"""

    def __init__(self, df: pd.DataFrame, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Melt Data")
        self.setModal(True)
        self.resize(800, 700)
        self.df = df
        self.columns = list(df.columns)
        self.row_count = df.shape[0]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        banner_widget = QWidget()
        banner_layout = QHBoxLayout(banner_widget)
        banner_layout.setContentsMargins(0, 0, 0, 5)
        
        icon_label = QLabel()
        icon_pixmap = QIcon(get_resource_path("icons/data_operations/melt_data.svg")).pixmap(42, 42)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        banner_layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        info_label = QLabel("Melt Data")
        info_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        text_layout.addWidget(info_label)
        

        info_description = QLabel(
            "Using melt you unpivot your data fra a wide format to a long format.\n"
            "1. Select ID variables (columns to keep as identifers).\n"
            "2. Select Value Variables (columns to unpivot into rows)."
        )
        info_description.setProperty("styleClass", "info_text")
        info_description.setWordWrap(True)
        text_layout.addWidget(info_description)
        
        banner_layout.addLayout(text_layout)
        banner_layout.addStretch()
        
        layout.addWidget(banner_widget)
        layout.addSpacing(5)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(20)
        splitter.setChildrenCollapsible(False)
        
        id_panel, self.id_variable_list, self.id_search_input = self._create_column_selection_panel(
            title="ID variables (Keep these columns)"
        )
        splitter.addWidget(id_panel)
        
        
        value_panel, self.value_list, self.value_search_input = self._create_column_selection_panel(
            title="Value Variables (Unpivot these):",
            hint="(Leave empty to unpivot all non-ID columns)"
        )
        splitter.addWidget(value_panel)
        
        layout.addWidget(splitter)
        layout.addSpacing(15)

        #naming
        naming_group = DataPlotStudioGroupBox("New Column Names")
        naming_layout = QFormLayout()

        self.variable_name_input = QLineEdit("variable")
        self.variable_name_input.setPlaceholderText("Name for the column containing old headers")
        naming_layout.addRow(QLabel("Variable Column Name:"), self.variable_name_input)

        self.value_name_input = QLineEdit("value")
        self.value_name_input.setPlaceholderText("Name for the column containing values")
        naming_layout.addRow(QLabel("Value Column Name:"), self.value_name_input)

        naming_group.setLayout(naming_layout)
        layout.addWidget(naming_group)

        preview_group = DataPlotStudioGroupBox("Preview")
        preview_layout = QVBoxLayout()

        self.preview_label = QLabel("Click 'Update Preview' to see changes")
        self.preview_label.setObjectName("melt_preview_label")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        header.setObjectName("MainDataHeader")
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_table)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        layout.addStretch()

        #buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_button = DataPlotStudioButton("Melt Data", base_color_hex=ThemeColors.MainColor)
        apply_button.setMinimumWidth(120)
        apply_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(apply_button)

        cancel_button = DataPlotStudioButton("Cancel")
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        
        self.id_variable_list.itemSelectionChanged.connect(self.update_preview)
        self.value_list.itemSelectionChanged.connect(self.update_preview)
        self.variable_name_input.textChanged.connect(self.update_preview)
        self.value_name_input.textChanged.connect(self.update_preview)
        
        self.update_preview()
    
    def _create_column_selection_panel(self, title: str, hint: str = "") -> Tuple[QWidget, DataPlotStudioListWidget, DataPlotStudioLineEdit]:
        panel_widget = QWidget()
        layout = QVBoxLayout(panel_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_label = QLabel(title)
        header_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        list_widget = DataPlotStudioListWidget()
        list_widget.setSelectionMode(DataPlotStudioListWidget.SelectionMode.MultiSelection)
        list_widget.addItems(self.columns)
        
        select_all_btn = DataPlotStudioButton("Select All")
        select_all_btn.setFlat(True)
        select_all_btn.setProperty("styleClass", "secondary_button")
        select_all_btn.clicked.connect(lambda: self._select_all_visible(list_widget))
        header_layout.addWidget(select_all_btn)
        
        clear_all_btn = DataPlotStudioButton("Clear All")
        clear_all_btn.setFlat(True)
        clear_all_btn.setProperty("styleClass", "secondary_button")
        clear_all_btn.clicked.connect(list_widget.clearSelection)
        header_layout.addWidget(clear_all_btn)
        
        layout.addLayout(header_layout)
        
        if hint:
            hint_label = QLabel(hint)
            hint_label.setProperty("styleClass", "muted_text")
            layout.addWidget(hint_label)
        
        search_input = DataPlotStudioLineEdit()
        search_input.setPlaceholderText("Filter columns...")
        search_input.setClearButtonEnabled(True)
        search_input.setProperty("styleClass", "seach_input")
        layout.addWidget(search_input)
        
        layout.addWidget(list_widget)
        
        count_label = QLabel()
        count_label.setProperty("styleClass", "muted_text")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(count_label)
        
        def update_selection_count() -> None:
            count = len(list_widget.selectedItems())
            total = list_widget.count()
            count_label.setText(f"{count} / {total} selected")
        list_widget.itemSelectionChanged.connect(update_selection_count)
        update_selection_count()
        
        search_input.textChanged.connect(lambda text, lw=list_widget: self._filter_list_widget(text, lw))

        return panel_widget, list_widget, search_input
    
    def _filter_list_widget(self, text: str, list_widget: DataPlotStudioListWidget) -> None:
        search_text = text.lower()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is not None:
                item.setHidden(search_text not in item.text().lower())
    
    def _select_all_visible(self, list_widget: DataPlotStudioListWidget) -> None:
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is not None and not item.isHidden():
                item.setSelected(True)

    def update_preview(self):
        """Calculate and display the expected shape of the new dataframe"""
        id_vars = [item.text() for item in self.id_variable_list.selectedItems()]
        value_vars = [item.text() for item in self.value_list.selectedItems()]

        overlap = set(id_vars) & set(value_vars)
        if overlap:
            self.preview_label.setText(f"Error: Overlap in ID and Value variables: {', '.join(overlap)}")
            self.preview_label.setProperty("status", "error")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
            self.preview_table.clear()
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return
        
        v_vars = value_vars if value_vars else None

        if not v_vars:
            num_value_vars = len(self.columns) - len(id_vars)
        else:
            num_value_vars = len(v_vars)
        
        new_rows = self.row_count * num_value_vars
        new_cols = len(id_vars) + 2
        try:
            df_slice = self.df.head(15).copy()
            
            var_name = self.variable_name_input.text() or "variable"
            value_name = self.value_name_input.text() or "value"

            preview_df = pd.melt(
                df_slice,
                id_vars=id_vars,
                value_vars=v_vars,
                var_name=var_name,
                value_name=value_name
            )

            self.preview_table.setRowCount(preview_df.shape[0])
            self.preview_table.setColumnCount(preview_df.shape[1])
            self.preview_table.setHorizontalHeaderLabels(list(preview_df.columns))
            
            bold_font = QFont()
            bold_font.setBold(True)

            for row in range(preview_df.shape[0]):
                for col in range(preview_df.shape[1]):
                    raw_val = preview_df.iat[row, col]
                    
                    if isinstance(raw_val, float):
                        val_str = f"{raw_val:.4f}"
                    else:
                        val_str = str(raw_val)
                    item = QTableWidgetItem(val_str)
                    
                    col_name = preview_df.columns[col]
                    if col_name in (var_name, value_name):
                        item.setFont(bold_font)
                    self.preview_table.setItem(row, col, item)
            
            text = (
                f"Original Shape: {self.df.shape}  ->  "
                f"Result Shape: ({new_rows}, {new_cols})"
            )
            status_state = "success"
            
            if new_rows > 1_000_000 or (self.row_count > 0 and new_rows > self.row_count * 20):
                text += f"\nWarning: Row count will increase by {num_value_vars}x!"
                status_state = "warning"

            self.preview_label.setText(text)
            self.preview_label.setProperty("status", status_state)
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
        
        except Exception as PreviewMeltError:
            self.preview_label.setText(f"Preview Error: {str(PreviewMeltError)}")
            self.preview_label.setProperty("status", "error")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)
            print(PreviewMeltError)

    def validate_and_accept(self):
        """Validate the inputs in melt"""
        id_vars = [item.text() for item in self.id_variable_list.selectedItems()]
        value_vars = [item.text() for item in self.value_list.selectedItems()]

        overlap = set(id_vars) & set(value_vars)
        if overlap:
            QMessageBox.warning(self, "Validation Error", f"Columns cannot be both ID and value variables:\n{', '.join(overlap)}")
            return
        
        var_name = self.variable_name_input.text().strip()
        value_name = self.value_name_input.text().strip()

        if not var_name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the Variable column.")
            return

        if not value_name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the Value column.")
            return
            
        if var_name == value_name:
            QMessageBox.warning(self, "Validation Error", "The Variable Column Name and Value Column Name cannot be identical.")
            return
            
        if var_name in id_vars or value_name in id_vars:
            QMessageBox.warning(self, "Validation Error", "The new column names cannot conflict with existing ID variables.")
            return

        self.accept()

    def get_config(self) -> Dict[str, Any]:
        """Return the config for this dialog"""
        return {
            "id_vars": [item.text() for item in self.id_variable_list.selectedItems()],
            "value_vars": [item.text() for item in self.value_list.selectedItems()],
            "var_name": self.variable_name_input.text().strip(),
            "value_name": self.value_name_input.text().strip()
        }