from PyQt6.QtWidgets import QVBoxLayout, QLabel, QAbstractItemView, QScrollArea, QFrame, QWidget, QListWidget, QGroupBox, QComboBox
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.icons import IconType

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController
    
class ColumnsTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()
    
    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        column_scroll_area = QScrollArea()
        column_scroll_area.setWidgetResizable(True)
        column_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        column_scroll_area.setProperty("styleClass", "transparent_scroll_area")
        
        inner_tab = QWidget()
        inner_tab.setObjectName("TransparentScrollContent")
        layout = QVBoxLayout(inner_tab)
        
        column_info = QLabel("This tab allows you to change certain elements to the columns of your data")
        column_info.setWordWrap(True)
        column_info.setProperty("styleClass", "info_text")
        layout.addWidget(column_info)

        column_column_info = QLabel("Select the column you wish to work with")
        column_column_info.setWordWrap(True)
        column_column_info.setProperty("styleClass", "info_text")
        layout.addWidget(column_column_info)
        
        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.column_list.setMaximumHeight(400)
        layout.addWidget(self.column_list)
        
        layout.addLayout(self._create_operation_row(
            title="Column Reorder Tool",
            tooltip="Open an interactive preview of your data to visually drag and drop column headers into a new order",
            callback=self.controller.open_column_reorder_dialog,
            help_id="reorder_columns",
            icon_type=IconType.DataTransform
        ))
        layout.addLayout(self._create_operation_row(
            title="Drop Column",
            tooltip="Use this to remove the selected column from the dataset",
            callback=self.controller.drop_column,
            help_id="drop_column",
            icon_type=IconType.DropColumn
        ))
        layout.addLayout(self._create_operation_row(
            title="Rename Column",
            tooltip="Use this to rename the selected column",
            callback=self.controller.rename_column,
            help_id="rename_column",
            icon_type=IconType.RenameColumn
        ))
        layout.addLayout(self._create_operation_row(
            title="Duplicate Column",
            tooltip="Create an exact copy of the selected column",
            callback=self.controller.duplicate_column,
            help_id="duplicate_column",
            icon_type=IconType.DuplicateColumn
        ))
        layout.addLayout(self._create_operation_row(
            title="Compute Column",
            tooltip="Create a new column based on a formula (eg Total = Price * Quantity)",
            callback=self.controller.open_computed_column_dialog,
            help_id="compute_column",
            icon_type=IconType.Calculator
        ))
        layout.addSpacing(10)
        
        # Data Type conversion
        type_group = QGroupBox("Change Data Type")
        type_layout = QVBoxLayout()
        data_type_info = QLabel("This operation allows you to change the datatype of your selected column")
        data_type_info.setWordWrap(True)
        data_type_info.setProperty("styleClass", "info_text")
        type_layout.addWidget(data_type_info)
        type_layout.addWidget(QLabel("Change selected columns DataType to:"))
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "string (object)", "integer (numeric)", "float (numeric)", "category (optimized string)", "datetime (dates/times)"
        ])
        type_layout.addWidget(self.type_combo)
        
        type_layout.addLayout(self._create_operation_row(
            title="Apply DataType Change",
            tooltip="Convert data type of the selected column",
            callback=self.controller.change_column_type,
            help_id="change_datatype",
            icon_type=IconType.ChangeDataType
        ))
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Text Manipulation
        layout.addSpacing(10)
        text_group = QGroupBox("Text Manipulation")
        text_layout = QVBoxLayout()
        text_info = QLabel("Standardize text data in the selected column.\nRemove whitespace, fix casing etc.")
        text_info.setWordWrap(True)
        text_info.setProperty("styleClass", "info_text")
        text_layout.addWidget(text_info)

        self.text_operation_combo = QComboBox()
        self.text_operation_combo.addItems([
            "Trim Whitespace", "Trim leading whitespace", "Trim trailing whitepsace",
            "Convert to lowercase", "Convert to UPPERCASE", "Convert to Title Case",
            "Capitalize First Letter",
        ])
        text_layout.addWidget(self.text_operation_combo)

        text_layout.addLayout(self._create_operation_row(
            title="Apply Text Operation",
            tooltip="Apply text standardization",
            callback=self.controller.apply_text_manipulation,
            help_id="text_manipulation",
            icon_type=IconType.TextOperation
        ))
        
        text_layout.addLayout(self._create_operation_row(
            title="Split Column",
            tooltip="Split a string column into multiple columns using a delimiter",
            callback=self.controller.open_split_column_dialog,
            help_id="split_column",
            icon_type=IconType.TextOperation
        ))
        
        text_layout.addLayout(self._create_operation_row(
            title="Regex Replace",
            tooltip="Replace text in a column using regular expressions",
            callback=self.controller.open_regex_replace_dialog,
            help_id="regex_replace",
            icon_type=IconType.TextOperation
        ))
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # Binning & Normalizatio
        layout.addSpacing(10)
        binning_group = QGroupBox("Binning / Discretization")
        binning_layout = QVBoxLayout()
        binning_info = QLabel("Convert continuous numeric variables into categorical buckets.")
        binning_info.setWordWrap(True)
        binning_info.setProperty("styleClass", "info_text")
        binning_layout.addWidget(binning_info)
        
        binning_layout.addLayout(self._create_operation_row(
            title="Bin / Discretize Column",
            tooltip="Open tool to create bins from numeric data",
            callback=self.controller.open_binning_dialog,
            help_id="binning_discretization",
            icon_type=IconType.DataTransform
        ))
        binning_group.setLayout(binning_layout)
        layout.addWidget(binning_group)
        
        layout.addSpacing(10)
        
        # Normalization
        norm_group = QGroupBox("Data Normalization and Scaling")
        norm_layout = QVBoxLayout()
        norm_info = QLabel("Scale numeric data to a standard range or distribution")
        norm_info.setWordWrap(True)
        norm_info.setProperty("styleClass", "info_text")
        norm_layout.addWidget(norm_info)
        
        self.norm_method_combo = QComboBox()
        self.norm_method_combo.addItems(["Min-Max Scaling", "Standard Scaling", "Median Scaling"])
        norm_layout.addWidget(self.norm_method_combo)
        
        norm_layout.addLayout(self._create_operation_row(
            title="Apply Scaling",
            tooltip="Apply the selected scaling technique to selected columns",
            callback=self.controller.apply_normalization,
            help_id="data_normalization",
            icon_type=IconType.DataTransform
        ))
        norm_group.setLayout(norm_layout)
        layout.addWidget(norm_group)

        layout.addStretch()
        column_scroll_area.setWidget(inner_tab)
        main_layout.addWidget(column_scroll_area)
    
    def get_selected_columns(self) -> list[str]:
        return [item.text() for item in self.column_list.selectedItems()]
    
    def get_target_datatype(self) -> str:
        return self.type_combo.currentText()

    def get_text_operation(self) -> str:
        return self.text_operation_combo.currentText()
    
    def get_normalization_method(self) -> str:
        return self.norm_method_combo.currentText()