from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QStackedWidget, QDateEdit, QWidget, QScrollArea, QPushButton, QSizePolicy, QCompleter
from PyQt6.QtCore import QDate, Qt
import pandas as pd
from typing import Dict, Any, List, Optional

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit


class CreateSubsetDialog(QDialog):
    """Dialog for creating andediting subsets"""

    ConditionMap = {
        'Equals (==)': '==',
        'Does Not Equal (!=)': '!=',
        'Greater Than (>)': '>',
        'Less Than (<)': '<',
        'Greater or Equal (>=)': '>=',
        'Less or Equal (<=)': '<=',
        'Contains Text': 'contains',
        'In List': 'in',
        'Is Null': 'Is Null',
        'Is Not Null': 'Is Not Null'
    }
    
    NumericConditions = [
        'Equals (==)', 'Does Not Equal (!=)', 'Greater Than (>)', 'Less Than (<)',
        'Greater or Equal (>=)', 'Less or Equal (<=)', 'Is Null', 'Is Not Null'
    ]
    
    StringConditions = [
        'Equals (==)', 'Does Not Equal (!=)', 'Contains Text', 'In List',
        'Is Null', 'Is Not Null'
    ]
    
    def __init__(self, data_handler, parent=None, existing_subset=None):
        super().__init__(parent)
        self.data_handler = data_handler
        self.columns = list(self.data_handler.df.columns) if self.data_handler.df is not None else []
        self.existing_subset = existing_subset
        self.filter_rows = []

        self.setWindowTitle("Create Subset" if not existing_subset else "Edit Subset")
        self.setModal(True)
        self.resize(900, 750)

        self.init_ui()

        if existing_subset:
            self.load_existing_subset()

    def init_ui(self):
        """Init the UI"""
        layout = QVBoxLayout()

        #name for the new subsets
        if not self.existing_subset:
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Subset Name:"))
            self.name_input = DataPlotStudioLineEdit()
            self.name_input.setPlaceholderText("e.g. high_values, location_A, etc")
            name_layout.addWidget(self.name_input)
            layout.addLayout(name_layout)

        #description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = DataPlotStudioLineEdit()
        self.desc_input.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)

        layout.addSpacing(10)
        
        #filter headers
        layout.addWidget(QLabel("Filters:"))
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setProperty("styleClass", "transparent_scroll_area")
        
        scroll_widget = QWidget()
        scroll_widget.setObjectName("TransparentScrollContent")
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area, 1)

        add_btn_layout = QHBoxLayout()
        self.add_filter_btn = DataPlotStudioButton("+ Add Filter", parent=self)
        self.add_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_filter_btn.setToolTip("Add another filter condition")
        self.add_filter_btn.clicked.connect(self.add_filter_row)
        add_btn_layout.addWidget(self.add_filter_btn)
        add_btn_layout.addStretch()
        layout.addLayout(add_btn_layout)
        
        if not self.existing_subset:
            self.add_filter_row()
            
        layout.addSpacing(20)

        # Buttons
        button_layout = QHBoxLayout()

        create_btn = DataPlotStudioButton("Create" if not self.existing_subset else "Update", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        create_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(create_btn)

        cancel_btn = DataPlotStudioButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def add_filter_row(self) -> None:
        """Adds a new filter configuration row to the dialog."""
        row_index = len(self.filter_rows)
        filter_group = DataPlotStudioGroupBox(f"Filter {row_index + 1}", parent=self)
        filter_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        filter_layout = QHBoxLayout()
        
        logic_combo = DataPlotStudioComboBox()
        logic_combo.addItems(["AND", "OR"])
        logic_combo.setFixedWidth(70)
        logic_combo.setToolTip("Logical operator to combine with preceding filters")
        
        sizepolicy = logic_combo.sizePolicy()
        sizepolicy.setRetainSizeWhenHidden(True)
        logic_combo.setSizePolicy(sizepolicy)
        
        if row_index == 0:
            logic_combo.setVisible(False)
        filter_layout.addWidget(logic_combo)

        # Column selector
        column_combo = DataPlotStudioComboBox()
        column_combo.addItems(self.columns)
        column_combo.setMinimumWidth(120)
        column_combo.setToolTip("Type to search or select a column")
        column_combo.setEditable(True)
        column_combo.setInsertPolicy(DataPlotStudioComboBox.InsertPolicy.NoInsert)
        column_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        
        col_label = QLabel("Column:")
        col_label.setFixedWidth(55)
        filter_layout.addWidget(col_label)
        filter_layout.addWidget(column_combo, 1)

        # Condition selector
        condition_combo = DataPlotStudioComboBox()
        condition_combo.addItems(list(self.ConditionMap.keys()))
        condition_combo.setMinimumWidth(170)
        condition_combo.setSizeAdjustPolicy(DataPlotStudioComboBox.SizeAdjustPolicy.AdjustToContents)
        cond_label = QLabel("Condition:")
        cond_label.setFixedWidth(65)
        filter_layout.addWidget(cond_label)
        filter_layout.addWidget(condition_combo, 0)
        
        input_stack = QStackedWidget()

        # Text input (0)
        text_input = DataPlotStudioLineEdit()
        text_input.setPlaceholderText("Enter text...")
        text_input.setClearButtonEnabled(True)
        input_stack.addWidget(text_input)
        
        # Numerical input (1)
        number_input = DataPlotStudioDoubleSpinBox()
        number_input.setRange(-999999999.0, 999999999.0)
        number_input.setDecimals(4)
        number_input.setGroupSeparatorShown(True)
        input_stack.addWidget(number_input)
        
        # Categorical input (2)
        category_input = DataPlotStudioComboBox()
        input_stack.addWidget(category_input)
        
        # Date input (3)
        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat("yyyy-MM-dd")
        date_input.setDate(QDate.currentDate())
        input_stack.addWidget(date_input)
        
        # Empty input for Null checks (4)
        empty_widget = DataPlotStudioLineEdit()
        empty_widget.setPlaceholderText("No value required")
        empty_widget.setEnabled(False)
        input_stack.addWidget(empty_widget)
        
        val_label = QLabel("Value:")
        val_label.setFixedWidth(40)
        filter_layout.addWidget(val_label)
        filter_layout.addWidget(input_stack, 2)
        
        remove_btn = QPushButton("✕")
        remove_btn.setToolTip("Remove this filter")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setFixedWidth(30)
        remove_btn.setProperty("styleClass", "remove_filter_btn")
        filter_layout.addWidget(remove_btn)

        filter_group.setLayout(filter_layout)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, filter_group)

        row_data = {
            'logic': logic_combo,
            'column': column_combo,
            'condition': condition_combo,
            'stack': input_stack,
            'inputs': {
                'text': text_input,
                'number': number_input,
                'category': category_input,
                'date': date_input
            },
            'group': filter_group
        }
        self.filter_rows.append(row_data)
        
        column_combo.currentTextChanged.connect(lambda _, r=row_data: self.update_row_ui(r))
        condition_combo.currentTextChanged.connect(lambda _, r=row_data: self.update_row_ui(r))
        remove_btn.clicked.connect(lambda _, r=row_data: self.remove_filter_row(r))
        
        self.update_row_ui(row_data)
        
        if row_index > 0:
            column_combo.setFocus()
    
    def remove_filter_row(self, row_data: Dict[str, Any]) -> None:
        """Remove a specific filter row and update UI"""
        if len(self.filter_rows) <= 1:
            if row_data["column"].count() > 0:
                row_data["column"].setCurrentIndex(0)
            row_data["condition"].setCurrentIndex(0)
            row_data['inputs']['text'].clear()
            row_data['inputs']['number'].setValue(0.0)
            return
        
        self.filter_rows.remove(row_data)
        row_data["group"].deleteLater()
        
        for i, row in enumerate(self.filter_rows):
            row["group"].setTitle(f"Filter {i+1}")
            if i == 0:
                row["logic"].setVisible(False)
            else:
                row["logic"].setVisible(True)
    
    
    def update_row_ui(self, row: Dict[str, Any]) -> None:
        """Updates the input widget based on the column data type and condition"""
        col_name = row["column"].currentText()
        cond_combo = row["condition"]
        
        df = self.data_handler.df
        if df is None or col_name not in df.columns:
            col_dtype = pd.Series(dtype="object").dtype
        else:
            col_dtype = df[col_name].dtype
            
        if pd.api.types.is_numeric_dtype(col_dtype) or pd.api.types.is_datetime64_any_dtype(col_dtype):
            valid_conditions = self.NumericConditions
        else:
            valid_conditions = self.StringConditions
            
        current_cond = cond_combo.currentText()
        current_items = [cond_combo.itemText(i) for i in range(cond_combo.count())]
        
        if current_items != valid_conditions:
            cond_combo.blockSignals(True)
            cond_combo.clear()
            cond_combo.addItems(valid_conditions)
            if current_cond in valid_conditions:
                cond_combo.setCurrentText(current_cond)
            else:
                cond_combo.setCurrentIndex(0)
            cond_combo.blockSignals(False)
            
        cond_display = cond_combo.currentText()
        condition = self.ConditionMap.get(cond_display, cond_display)
        stack = row["stack"]
        
        if condition in ["Is Null", "Is Not Null"]:
            stack.setCurrentIndex(4)
            return
        
        if pd.api.types.is_numeric_dtype(col_dtype):
            stack.setCurrentIndex(1)
            valid_numbers = df[col_name].dropna()
            if not valid_numbers.empty:
                min_val = float(valid_numbers.min())
                max_val = float(valid_numbers.max())
                margin = abs(max_val - min_val) * 0.1 if max_val != min_val else 10.0
                row["inputs"]["number"].setRange(min_val - margin, max_val + margin)
        elif pd.api.types.is_datetime64_any_dtype(col_dtype):
            stack.setCurrentIndex(3)
            valid_dates = df[col_name].dropna()
            if not valid_dates.empty:
                max_date = valid_dates.max()
                try:
                    qdate = QDate(max_date.year, max_date.month, max_date.day)
                    if qdate.isValid():
                        row["inputs"]["date"].setDate(qdate)
                except Exception:
                    pass
        elif pd.api.types.is_object_dtype(col_dtype) or pd.api.types.is_categorical_dtype(col_dtype) or pd.api.types.is_string_dtype(col_dtype):
            unique_vals = df[col_name].dropna().unique()
            if len(unique_vals) < 1000:
                stack.setCurrentIndex(2)
                combo = row["inputs"]["category"]
                sorted_vals = sorted([str(v) for v in unique_vals])
                current_vals = [combo.itemText(i) for i in range(combo.count())]
                if current_vals != sorted_vals:
                    combo.clear()
                    combo.addItems(sorted_vals)
                combo.setEditable(True)
                combo.setInsertPolicy(DataPlotStudioComboBox.InsertPolicy.NoInsert)
                
                completer = QCompleter(sorted_vals, combo)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
                combo.setCompleter(completer)
            else:
                stack.setCurrentIndex(0)
                self._update_text_placeholder(row, condition)
        else:
            stack.setCurrentIndex(0)
            self._update_text_placeholder(row, condition)
    
    def _update_text_placeholder(self, row: Dict[str, Any], condition: str) -> None:
        """Dynamically update placeholder text to guide the user based on the selected condition."""
        text_widget = row["inputs"]["text"]
        if condition == "contains":
            text_widget.setPlaceholderText("Enter substring...")
        elif condition == "in":
            text_widget.setPlaceholderText("e.g. val1, val2, val3")
        else:
            text_widget.setPlaceholderText("Enter text...")
    
    def get_current_value(self, row: Dict[str, Any]) -> Any:
        """Retrieve the value from the active widget"""
        idx = row["stack"].currentIndex()
        if idx == 0:
            return row["inputs"]["text"].text().strip()
        if idx == 1:
            return row["inputs"]["number"].value()
        if idx == 2:
            return row["inputs"]["category"].currentText()
        if idx == 3:
            return row["inputs"]["date"].date().toString("yyyy-MM-dd")
        return None

    def load_existing_subset(self) -> None:
        """Load an existing subset into the form"""
        self.desc_input.setText(self.existing_subset.description)
        
        filters = self.existing_subset.filters
        legacy_logic = getattr(self.existing_subset, "logic", "AND")
        
        for i, f_def in enumerate(filters):
            if i >= len(self.filter_rows):
                self.add_filter_row()
                
            row = self.filter_rows[i]
            row["column"].setCurrentText(f_def["column"])
            
            saved_cond = f_def["condition"]
            display_cond = next((k for k, v in self.ConditionMap.items() if v == saved_cond), saved_cond)
            row["condition"].setCurrentText(display_cond)
            
            val = f_def["value"]
            if val is not None:
                row["inputs"]["text"].setText(str(val))
                try:
                    if isinstance(val, (int, float)):
                        row["inputs"]["number"].setValue(float(val))
                except ValueError:
                    pass
                
                if row["inputs"]["category"].findText(str(val)) != -1:
                    row["inputs"]["category"].setCurrentText(str(val))
                else:
                    row["inputs"]["category"].setCurrentText(str(val))
                
                try:
                    parsed_date = QDate.fromString(str(val), "yyyy-MM-dd")
                    if parsed_date.isValid():
                        row["inputs"]["date"].setDate(parsed_date)
                except Exception:
                    pass
                
            if i > 0:
                op = f_def.get("operator", legacy_logic)
                row["logic"].setCurrentText(op if op else "AND")

    def validate_and_accept(self) -> None:
        """Validate and accept"""
        if not self.existing_subset:
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Validation Error", "Please enter a subset name")
                return

        if not self.filter_rows:
            QMessageBox.warning(self, "Validation Error", "Please create at least one filter")
            return

        for row in self.filter_rows:
            cond_display = row["condition"].currentText()
            cond = self.ConditionMap.get(cond_display, cond_display)
            val = self.get_current_value(row)
            
            if cond not in ["Is Null", "Is Not Null"]:
                if isinstance(val, str) and not val.strip():
                    QMessageBox.warning(self, "Validation Error", "Please enter values for all filters")
                    return
        self.accept()

    def get_config(self) -> Dict[str, Any]:
        """Returns the subset config"""
        filters: List[Dict[str, Any]] = []
        
        for i, row in enumerate(self.filter_rows):
            cond_display = row['condition'].currentText()
            filters.append({
                'operator': None if i == 0 else row["logic"].currentText(),
                'column': row['column'].currentText(),
                'condition': self.ConditionMap.get(cond_display, cond_display),
                'value': self.get_current_value(row)
            })

        config: Dict[str, Any] = {
            'description': self.desc_input.text().strip(),
            'filters': filters,
            'logic': "COMPLEX"
        }

        if not self.existing_subset:
            config['name'] = self.name_input.text().strip()

        return config