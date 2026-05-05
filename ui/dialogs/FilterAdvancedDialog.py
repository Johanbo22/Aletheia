from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QStackedWidget, QDateEdit, QSizePolicy, QWidget, QCompleter, QScrollArea, QPushButton
from PyQt6.QtCore import QDate, QThreadPool, Qt, QTimer
import pandas as pd
from typing import List, Dict, Any, Optional

from ui.theme import ThemeColors
from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit
from ui.workers import FilterWorker
from ui.widgets import DataPlotStudioButton
from ui.icons import IconBuilder, IconType


class FilterAdvancedDialog(QDialog):
    """Dialog for advanced filtering with multiple conditions"""
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

    def __init__(self, data_handler, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Filter")
        self.setModal(True)
        self.setMinimumSize(900, 600)

        self.data_handler = data_handler
        self.columns = list(self.data_handler.df.columns) if self.data_handler.df is not None else []
        self.filters = []
        self.thread_pool = QThreadPool.globalInstance()
        self._column_stats_cache: Dict[str, Dict[str, Any]] = {}
        
        # Timer for the preview_label to not lag
        PREVIEW_TIMER_MS = 250
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_TIMER_MS)
        self._preview_timer.timeout.connect(self._render_preview)
        
        self.init_ui()
    
    @property
    def _has_active_filters(self) -> bool:
        """Determines if there are any configured filters based on widget states"""
        if len(self.filter_rows) > 1:
            return True
        if self.filter_rows:
            first_row = self.filter_rows[0]
            val = self.get_current_value(first_row)
            condition = first_row["condition"].currentText()
            if val != "" or condition in ["Is Null", "Is Not Null"]:
                return True
        return False
        
    def reject(self) -> None:
        """Override of self.reject to prevent accidental data loss on Escape key or Cancel button."""
        if self._has_active_filters:
            reply = QMessageBox.question(
                self, 'Cancel Filtering', 
                'You have active filter configurations. Are you sure you want to cancel?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        super().reject()

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout(self)

        instruction_label = QLabel("Construct filter query:")
        instruction_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        layout.addWidget(instruction_label)
        layout.addSpacing(10)

        layout.addSpacing(19)

        # preview text
        self.preview_label = QLabel("Preview: No filters active")
        self.preview_label.setWordWrap(True)
        self.preview_label.setObjectName("filter_preview_label")
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setProperty("styleClass", "transparent_scroll_area")
        
        scroll_widget = QWidget()
        scroll_widget.setObjectName("TransparentScrollContent")
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.addStretch()
        
        self.filter_rows = []
        
        self.add_filter_row()
        self.scroll_area.setWidget(scroll_widget)
        layout.addWidget(self.scroll_area, 1)
        
        add_btn_layout = QHBoxLayout()
        self.add_filter_btn = DataPlotStudioButton("+ Add Filter", parent=self)
        self.add_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_filter_btn.setToolTip("Add another filter condition")
        self.add_filter_btn.clicked.connect(self.add_filter_row)
        add_btn_layout.addWidget(self.add_filter_btn)
        add_btn_layout.addStretch()
        layout.addLayout(add_btn_layout)
        
        layout.addSpacing(15)
        layout.addWidget(self.preview_label)
        layout.addSpacing(10)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.apply_button = DataPlotStudioButton("Apply Filters", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        self.apply_button.clicked.connect(self.validate_and_accept)
        self.apply_button.setDefault(True)
        self.apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_button.setToolTip("Apply the constructed filter query to the dataset (Enter)")
        button_layout.addWidget(self.apply_button)

        clear_button = DataPlotStudioButton("Clear Filters", parent=self, base_color_hex=ThemeColors.DestructiveColor, text_color_hex="white")
        clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(clear_button)

        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.update_preview()
    
    def add_filter_row(self) -> None:
        """ adds a new filter configuration row to the dialog."""
        row_index = len(self.filter_rows)
        filter_group = DataPlotStudioGroupBox(f"Filter {row_index +1}", parent=self)
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

        # text input
        text_input = DataPlotStudioLineEdit()
        text_input.setPlaceholderText("Enter text...")
        text_input.setClearButtonEnabled(True)
        text_input.returnPressed.connect(self.validate_and_accept)
        input_stack.addWidget(text_input)
        
        # Numerical inputs
        number_input = DataPlotStudioDoubleSpinBox()
        number_input.setRange(-999999999, 999999999)
        number_input.setDecimals(4)
        number_input.setGroupSeparatorShown(True)
        input_stack.addWidget(number_input)
        
        # categorical INputs
        category_input = DataPlotStudioComboBox()
        input_stack.addWidget(category_input)
        
        # date input
        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat("yyyy-MM-dd")
        date_input.setDate(QDate.currentDate())
        input_stack.addWidget(date_input)
        
        # Explicit state for Null checks
        empty_widget = DataPlotStudioLineEdit()
        empty_widget.setPlaceholderText("No value required")
        empty_widget.setEnabled(False)
        input_stack.addWidget(empty_widget)
        
        val_label = QLabel("Value:")
        val_label.setFixedWidth(40)
        filter_layout.addWidget(val_label)
        filter_layout.addWidget(input_stack, 2)
        
        remove_btn = QPushButton()
        remove_btn.setIcon(IconBuilder.build(IconType.Close))
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
            'val_label': val_label,
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
        logic_combo.currentTextChanged.connect(self.update_preview)
        text_input.textChanged.connect(self.update_preview)
        number_input.valueChanged.connect(self.update_preview)
        category_input.currentTextChanged.connect(self.update_preview)
        date_input.dateChanged.connect(self.update_preview)
        remove_btn.clicked.connect(lambda _, r=row_data: self.remove_filter_row(r))
        
        self.update_row_ui(row_data)
        
        if row_index > 0:
            column_combo.setFocus()
            
        self.update_preview()
        QTimer.singleShot(10, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self) -> None:
        """Scrolls to the bottom of the filter list"""
        if hasattr(self, "scroll_area"):
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def remove_filter_row(self, row_data: dict) -> None:
        """Remove a specific filter row and update UI"""
        if len(self.filter_rows) <= 1:
            if row_data["column"].count() > 0:
                row_data["column"].setCurrentIndex(0)
            row_data["condition"].setCurrentIndex(0)
            row_data['inputs']['text'].clear()
            row_data['inputs']['number'].setValue(0)
            return
        
        self.filter_rows.remove(row_data)
        row_data["group"].deleteLater()
        
        for i, row in enumerate(self.filter_rows):
            row["group"].setTitle(f"Filter {i+1}")
            if i == 0:
                row["logic"].setVisible(False)
            else:
                row["logic"].setVisible(True)
        self.update_preview()
    
    def update_row_ui(self, row: dict):
        """Update the input widget based on the datatype of selected column and the selected condition"""
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
        val_label = row["val_label"]
        
        if condition in ["Is Null", "Is Not Null"]:
            stack.setCurrentIndex(4)
            stack.setVisible(False)
            val_label.setVisible(False)
            self.update_preview()
            return

        stack.setVisible(True)
        val_label.setVisible(True)
        
        if col_name not in self._column_stats_cache:
            stats: Dict[str, Any] = {}
            
            if df is not None and col_name in df.columns:
                col_data = df[col_name].dropna()
            
                if pd.api.types.is_numeric_dtype(col_dtype):
                    if not col_data.empty:
                        stats["min"] = float(col_data.min())
                        stats["max"] = float(col_data.max())
                    elif pd.api.types.is_datetime64_any_dtype(col_dtype):
                        if not col_data.empty:
                            stats["max_date"] = col_data.max()
                    elif pd.api.types.is_object_dtype(col_dtype) or pd.api.types.is_categorical_dtype(col_dtype) or pd.api.types.is_string_dtype(col_dtype):
                        unique_vals = col_data.unique()
                        if len(unique_vals) < 1000:
                            stats["unique"] = sorted([str(v) for v in unique_vals])
                
                self._column_stats_cache[col_name] = stats
            
        col_stats = self._column_stats_cache.get(col_name, {})
        
        if pd.api.types.is_numeric_dtype(col_dtype):
            number_index = 1
            stack.setCurrentIndex(number_index)
            if "min" in col_stats and "max" in col_stats:
                min_val = col_stats["min"]
                max_val = col_stats["max"]
                margin = abs(max_val - min_val) * 0.1 if max_val != min_val else 10.0
                spinbox = row["inputs"]["number"]
                spinbox.setRange(min_val - margin, max_val + margin)
                
                range_span = abs(max_val - min_val)
                if range_span == 0:
                    step_size = 1.0
                elif range_span <= 10.0:
                    step_size = 0.1
                elif range_span <= 100.0:
                    step_size = 1.0
                else:
                    step_size = round(range_span / 100.0)
                
                spinbox.setSingleStep(step_size)
                
        elif pd.api.types.is_datetime64_any_dtype(col_dtype):
            datetime_index = 3
            stack.setCurrentIndex(datetime_index)
            if "max_date" in col_stats:
                max_date = col_stats["max_date"]
                try:
                    qdate = QDate(max_date.year, max_date.month, max_date.day)
                    if qdate.isValid():
                        row["inputs"]["date"].setDate(qdate)
                except Exception:
                    pass
        elif pd.api.types.is_object_dtype(col_dtype) or pd.api.types.is_categorical_dtype(col_dtype) or pd.api.types.is_string_dtype(col_dtype):
            if "unique" in col_stats:
                unique_vals_index = 2
                stack.setCurrentIndex(unique_vals_index)
                combo = row["inputs"]["category"]
                
                sorted_vals = col_stats["unique"]
                current_vals = [combo.itemText(i) for i in range(combo.count())]
                if current_vals != sorted_vals:
                    combo.clear()
                    combo.addItems(sorted_vals)
                    if combo.lineEdit():
                        combo.lineEdit().clear()
                combo.setEditable(True)
                combo.setInsertPolicy(DataPlotStudioComboBox.InsertPolicy.NoInsert)
                if combo.lineEdit():
                    combo.lineEdit().setPlaceholderText("Select or type...")
                    try:
                        combo.lineEdit().returnPressed.disconnect()
                    except TypeError:
                        pass
                    combo.lineEdit().returnPressed.connect(self.validate_and_accept)
                
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
        
        active_widget = stack.currentWidget()
        if active_widget.isVisible() and active_widget.isEnabled():
            active_widget.setFocus()
        
        self.update_preview()
    
    def _update_text_placeholder(self, row: dict, condition: str) -> None:
        """Dynamically update placeholder text to guide the user based on the selected condition."""
        text_widget = row["inputs"]["text"]
        if condition == "contains":
            text_widget.setPlaceholderText("Enter substring...")
        elif condition == "in":
            text_widget.setPlaceholderText("e.g. val1, val2, val3")
        else:
            text_widget.setPlaceholderText("Enter text...")
            
    def _update_condition_options(self, row: dict, col_name: str) -> None:
        """Only show conditions that make sense for the columns datatype"""
        if self.data_handler.df is None and col_name in self.data_handler.df.columns:
            combo = row["condition"]
            current_cond = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            
            col_dtype = self.data_handler.df[col_name].dtype
            
            if pd.api.types.is_numeric_dtype(col_dtype):
                options = ["Equals", "Not Equals", "Greather Than", "Less Than", "Is Null", "Is Not Null"]
            elif pd.api.types.is_datetime64_any_dtype(col_dtype):
                options = ["Equals", "Before", "After", "Is Null", "Is Not Null"]
            else:
                options = ["Equals", "Not Equals", "Contains Text", "Starts With", "Ends With", "In List", "Is Null", "Is Not Null"]
            
            combo.addItems(options)
            
            if current_cond in options:
                combo.setCurrentText(current_cond)
            
            combo.blockSignals(False)
            self._on_condition_changed(row, combo.currentText())
    
    def _on_condition_changed(self, row: dict, condition: str) -> None:
        input_container = row.get("inputs")
        if condition in ["Is Null", "Is Not Null"]:
            if input_container:
                input_container.setVisible(False)
        else:
            if input_container:
                input_container.setVisible(True)
            
            active_widget = row["inputs"]["stack"].currentWidget()
            if active_widget.isVisible() and active_widget.isEnabled():
                active_widget.setFocus()
        self.update_preview()
    
    def get_current_value(self, row):
        """Retrieve the value from the current active widget"""
        stack_index = row["stack"].currentIndex()
        
        if stack_index == 0:
            return row["inputs"]["text"].text().strip()
        elif stack_index == 1:
            return row["inputs"]["number"].value()
        elif stack_index == 2:
            return row["inputs"]["category"].currentText()
        elif stack_index == 3:
            return row["inputs"]["date"].date().toString("yyyy-MM-dd")
        elif stack_index == 4:
            return None
        return ""

    def clear_fields(self):
        """Reset the filter fields to default"""
        if self._has_active_filters:
            reply = QMessageBox.question(
                self, 'Clear Filters', 
                'Are you sure you want to clear all filters?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        while len(self.filter_rows) > 1:
            self.remove_filter_row(self.filter_rows[-1])

        row = self.filter_rows[0]
        if row["column"].count() > 0:
            row["column"].setCurrentIndex(0)
        row["condition"].setCurrentIndex(0)
        row['inputs']['text'].clear()
        row['inputs']['number'].setValue(0)
        row['inputs']['date'].setDate(QDate.currentDate())

        self.update_preview()

    def update_preview(self) -> None:
        """Debounce the preview rendering from self.preview_timer"""
        if hasattr(self, "_preview_timer"):
            self._preview_timer.start()
        else:
            self._render_preview()
    
    def _render_preview(self):
        """update the filter preview"""
        preview_parts = []
        
        for i, row in enumerate(self.filter_rows):
            col = row["column"].currentText()
            cond_display = row["condition"].currentText()
            cond = self.ConditionMap.get(cond_display, cond_display)
            val = self.get_current_value(row)
            
            part = ""
            if cond in ["Is Null", "Is Not Null"]:
                part = f"<b>{col}</b> {cond}"
            else:
                part = f"<b>{col}</b> {cond} '<i>{val}</i>'"
            
            if i > 0 and preview_parts:
                logic = row["logic"].currentText()
                part = f" <span style='color: #0055A4; font-weight: bold;'>{logic}</span> {part}"
            
            preview_parts.append(part)
        
        text = "".join(preview_parts)
        if text:
            self.preview_label.setText(f"Preview: {text}")
        else:
            self.preview_label.setText("Preview: No filters active")
            
        is_fully_valid = False
        if text:
            is_fully_valid = True
            for row in self.filter_rows:
                row["inputs"]["text"].setProperty("validationState", "normal")
                row["inputs"]["text"].style().unpolish(row["inputs"]["text"])
                row["inputs"]["text"].style().polish(row["inputs"]["text"])
                
                cond_display = row["condition"].currentText()
                cond = self.ConditionMap.get(cond_display, cond_display)
                if cond not in ["Is Null", "Is Not Null"]:
                    val = self.get_current_value(row)
                    if isinstance(val, str) and not val:
                        is_fully_valid = False
                        if row["stack"].currentIndex() == 0:
                            row["inputs"]["text"].setProperty("validationState", "error")
                            row["inputs"]["text"].style().unpolish(row["inputs"]["text"])
                            row["inputs"]["text"].style().polish(row["inputs"]["text"])

        if hasattr(self, 'apply_button'):
            self.apply_button.setEnabled(is_fully_valid)
            if not is_fully_valid and text:
                self.apply_button.setToolTip("Missing input: Please enter a value for all active filters")
            else:
                self.apply_button.setToolTip("Apply the constructed filter query to the dataset (Enter)")

    def validate_and_accept(self):
        """Validate filters before accepting"""
        if not self.filter_rows:
            return

        for row in self.filter_rows:
            cond_display = row["condition"].currentText()
            cond = self.ConditionMap.get(cond_display, cond_display)
            val = self.get_current_value(row)
            if cond not in ["Is Null", "Is Not Null"]:
                if isinstance(val, str) and not val.strip():
                    return
        
        self.apply_button.setText("Applying...")
        self.apply_button.setEnabled(False)
        self.setEnabled(False)
        
        filter_config = self.get_filters()
        
        worker = FilterWorker(self.data_handler, filter_config)
        worker.signals.finished.connect(self.on_filter_finished)
        worker.signals.error.connect(self.on_filter_error)
        self.thread_pool.start(worker)
    
    def on_filter_finished(self, result_df):
        self.apply_button.setText("Apply Filters")
        self.data_handler.df = result_df
        self.setEnabled(True)
        self.accept()
    
    def on_filter_error(self, error):
        self.apply_button.setText("Apply Filters")
        self.setEnabled(True)
        QMessageBox.critical(self, "Filter error", f"An error occurred during filtering:\n{str(error)}")

    def get_filters(self):
        """Return active filters with logical operator"""
        filters = []
        for i, row in enumerate(self.filter_rows):
            cond_display = row["condition"].currentText()
            filters.append({
                "operator": row["logic"].currentText() if i > 0 else None,
                "column": row["column"].currentText(),
                "condition": self.ConditionMap.get(cond_display, cond_display),
                "value": self.get_current_value(row)
            })
        
        return {
            "logic": "COMPLEX",
            "filters": filters
        }