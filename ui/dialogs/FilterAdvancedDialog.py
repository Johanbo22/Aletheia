from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QStackedWidget, QDateEdit, QSizePolicy, QWidget, QCompleter, QScrollArea, QPushButton, QGraphicsOpacityEffect, QApplication, QLineEdit, QGroupBox, QDoubleSpinBox, QComboBox
from PyQt6.QtCore import QDate, QThreadPool, Qt, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
import pandas as pd
from typing import List, Dict, Any, Optional

from ui.theme import ThemeColors
from ui.workers import FilterWorker
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
        self._active_animations: List[QPropertyAnimation] = []
        
        # Timer for the preview_label to not lag
        PREVIEW_TIMER_MS = 250
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_TIMER_MS)
        self._preview_timer.timeout.connect(self._render_preview)

        loading_timer_ms = 400
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(loading_timer_ms)
        self._loading_timer.timeout.connect(self._update_loading_text)
        self._loading_dots = 0

        self._setup_shortcuts()
        
        self.init_ui()

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts"""
        add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        add_shortcut.activated.connect(self.add_filter_row)
        add_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        clear_shortcut = QShortcut(QKeySequence("Ctrl+Del"), self)
        clear_shortcut.activated.connect(self.clear_fields)
        clear_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    
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

        if hasattr(self, "_preview_timer"):
            self._preview_timer.stop()
        if hasattr(self, "_loading_timer"):
            self._loading_timer.stop()
        super().reject()

    def accept(self) -> None:
        if hasattr(self, '_preview_timer'):
            self._preview_timer.stop()
        if hasattr(self, '_loading_timer'):
            self._loading_timer.stop()
        super().accept()

    def closeEvent(self, event) -> None:
        if hasattr(self, '_preview_timer'):
            self._preview_timer.stop()
        if hasattr(self, '_loading_timer'):
            self._loading_timer.stop()
        super().closeEvent(event)

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
        self.add_filter_btn = QPushButton("+ Add Filter", parent=self)
        self.add_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_filter_btn.setToolTip("Add another filter condition")
        self.add_filter_btn.clicked.connect(self.add_filter_row)
        add_btn_layout.addWidget(self.add_filter_btn)
        add_btn_layout.addStretch()
        layout.addLayout(add_btn_layout)
        layout.addSpacing(15)

        # Preview Container
        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        preview_layout.addWidget(self.preview_label)

        self.copy_btn = QPushButton("Copy Query", parent=self)
        self.copy_btn.setToolTip("Copy the raw filter query to the system clipboard")
        self.copy_btn.clicked.connect(self._copy_query_to_clipboard)
        self.copy_btn.setVisible(False)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        preview_layout.addLayout(btn_layout)

        layout.addWidget(preview_container)
        layout.addSpacing(10)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.apply_button = QPushButton("Apply Filters")
        self.apply_button.setObjectName("MainActionButton")
        self.apply_button.clicked.connect(self.validate_and_accept)
        self.apply_button.setDefault(True)
        self.apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_button.setToolTip("Apply the constructed filter query to the dataset (Enter)")
        button_layout.addWidget(self.apply_button)

        clear_button = QPushButton("Clear Filters")
        clear_button.setObjectName("DestructiveButton")
        clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(clear_button)

        cancel_button = QPushButton("Cancel", parent=self)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.update_preview()

    def _update_logic_styling(self, row: dict, logic: str) -> None:
        """Update the visual border styling of the group box based on the logic operator"""
        group = row["group"]
        if logic == "ROOT":
            group.setTitle("Where...")
            group.setProperty("logicStyle", "root")
        elif logic == "AND":
            group.setTitle("And...")
            group.setProperty("logicStyle", "and")
        else:
            group.setTitle("Or...")
            group.setProperty("logicStyle", "or")

        group.style().unpolish(group)
        group.style().polish(group)

    def _copy_query_to_clipboard(self) -> None:
        """Extracts the raw query text to system clipboard with a visual confrmation"""
        if hasattr(self, "_current_raw_query") and self._current_raw_query:
            QApplication.clipboard().setText(self._current_raw_query)
            self.copy_btn.setText("Copied!")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy Query") if hasattr(self, "copy_btn") else None)

    def _cleanup_effect_animation(self, anim: QPropertyAnimation, widget: QWidget) -> None:
        """Restores native rendering after a fade animation completes"""
        if anim in self._active_animations:
            self._active_animations.remove(anim)
        if widget:
            widget.setGraphicsEffect(None)
    
    def add_filter_row(self) -> None:
        """ adds a new filter configuration row to the dialog."""
        row_index = len(self.filter_rows)
        filter_group = QGroupBox(f"Filter {row_index +1}", parent=self)
        filter_group.setObjectName("FilterGroupBox")
        filter_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        filter_layout = QHBoxLayout()
        
        logic_combo = QComboBox()
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
        column_combo = QComboBox()
        column_combo.addItems(self.columns)
        column_combo.setMinimumWidth(120)
        column_combo.setToolTip("Type to search or select a column")
        column_combo.setEditable(True)
        column_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        column_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        
        col_label = QLabel("Column:")
        col_label.setFixedWidth(55)
        filter_layout.addWidget(col_label)
        filter_layout.addWidget(column_combo, 1)

        # Condition selector
        condition_combo = QComboBox()
        condition_combo.addItems(list(self.ConditionMap.keys()))
        condition_combo.setMinimumWidth(170)
        condition_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        cond_label = QLabel("Condition:")
        cond_label.setFixedWidth(65)
        filter_layout.addWidget(cond_label)
        filter_layout.addWidget(condition_combo, 0)
        
        input_stack = QStackedWidget()

        # text input
        text_input = QLineEdit()
        text_input.setPlaceholderText("Enter text...")
        text_input.setClearButtonEnabled(True)
        text_input.returnPressed.connect(self.validate_and_accept)
        input_stack.addWidget(text_input)
        
        # Numerical inputs
        number_input = QDoubleSpinBox()
        number_input.setRange(-999999999, 999999999)
        number_input.setDecimals(4)
        number_input.setGroupSeparatorShown(True)
        input_stack.addWidget(number_input)
        
        # categorical INputs
        category_input = QComboBox()
        input_stack.addWidget(category_input)
        
        # date input
        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat("yyyy-MM-dd")
        date_input.setDate(QDate.currentDate())
        input_stack.addWidget(date_input)
        
        # Explicit state for Null checks
        empty_widget = QLineEdit()
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

        # Animation states
        effect = QGraphicsOpacityEffect(filter_group)
        filter_group.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        filter_group.setMaximumHeight(0)
        
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

        # Execute animation sequence
        anim_group = QParallelAnimationGroup(self)

        height_anim = QPropertyAnimation(filter_group, b"maximumHeight")
        height_anim.setDuration(250)
        height_anim.setStartValue(0)
        height_anim.setEndValue(120)
        height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        opacity_anim = QPropertyAnimation(effect, b"opacity")
        opacity_anim.setDuration(250)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        anim_group.addAnimation(height_anim)
        anim_group.addAnimation(opacity_anim)

        self._active_animations.append(anim_group)
        anim_group.finished.connect(lambda: self._active_animations.remove(anim_group) if anim_group in self._active_animations else None)
        anim_group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        
        column_combo.currentTextChanged.connect(lambda _, r=row_data: self.update_row_ui(r))
        condition_combo.currentTextChanged.connect(lambda _, r=row_data: self.update_row_ui(r))
        logic_combo.currentTextChanged.connect(self.update_preview)

        logic_combo.currentTextChanged.connect(lambda text, r=row_data: self._update_logic_styling(r, text))

        text_input.textChanged.connect(self.update_preview)
        number_input.valueChanged.connect(self.update_preview)
        category_input.currentTextChanged.connect(self.update_preview)
        date_input.dateChanged.connect(self.update_preview)
        remove_btn.clicked.connect(lambda _, r=row_data: self.remove_filter_row(r))
        
        self.update_row_ui(row_data)
        self._update_logic_styling(row_data, "ROOT" if row_index == 0 else logic_combo.currentText())
        
        if row_index > 0:
            column_combo.setFocus()
            
        self.update_preview()
        QTimer.singleShot(60, self._scroll_to_bottom)
    
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
        group = row_data["group"]

        effect = group.graphicsEffect()
        if not effect:
            effect = QGraphicsOpacityEffect(group)
            group.setGraphicsEffect(group)

        anim_group = QParallelAnimationGroup(self)

        height_anim = QPropertyAnimation(group, b"maximumHeight")
        height_anim.setDuration(200)
        height_anim.setStartValue(group.height())
        height_anim.setEndValue(0)
        height_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        opacity_anim = QPropertyAnimation(effect, b"opacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        anim_group.addAnimation(height_anim)
        anim_group.addAnimation(opacity_anim)

        self._active_animations.append(anim_group)

        def _on_remove_finished():
            group.deleteLater()
            if anim_group in self._active_animations:
                self._active_animations.remove(anim_group)
            self.update_preview()

        anim_group.finished.connect(_on_remove_finished)
        anim_group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        for i, row in enumerate(self.filter_rows):
            if i == 0:
                row["logic"].setVisible(False)
                self._update_logic_styling(row, "ROOT")
            else:
                row["logic"].setVisible(True)
                self._update_logic_styling(row, row["logic"].currentText())
    
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
                        sample_data = col_data if len(col_data) <= 500000 else col_data.head(500000)
                        unique_vals = sample_data.unique()
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
                combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
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

            effect = QGraphicsOpacityEffect(active_widget)
            active_widget.setGraphicsEffect(effect)
            morph_anim = QPropertyAnimation(effect, b"opacity")
            morph_anim.setDuration(250)
            morph_anim.setStartValue(0.0)
            morph_anim.setEndValue(1.0)
            morph_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            self._active_animations.append(morph_anim)
            morph_anim.finished.connect(lambda: self._cleanup_effect_animation(morph_anim, active_widget))
            morph_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        
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
        cond_display = row["condition"].currentText()
        condition = self.ConditionMap.get(cond_display, cond_display)

        if stack_index == 0:
            val = row["inputs"]["text"].text().strip()
            if condition == "in" and val:
                cleaned_items = [item.strip() for item in val.split(",")]
                return ", ".join(filter(None, cleaned_items))
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

        rows_to_remove = self.filter_rows[1:]

        def _cascade_remove() -> None:
            """Recursively pops and removes rows with a slight delay"""
            if rows_to_remove:
                row = rows_to_remove.pop()
                self.remove_filter_row(row)
                QTimer.singleShot(75, _cascade_remove)
            else:
                row = self.filter_rows[0]
                if row["column"].count() > 0:
                    row["column"].setCurrentIndex(0)
                row["condition"].setCurrentIndex(0)
                row['inputs']['text'].clear()
                row['inputs']['number'].setValue(0)
                row['inputs']['date'].setDate(QDate.currentDate())
                self.update_preview()
        _cascade_remove()

    def update_preview(self) -> None:
        """Debounce the preview rendering from self.preview_timer"""
        if hasattr(self, "_preview_timer"):
            self._preview_timer.start()
        else:
            self._render_preview()
    
    def _render_preview(self):
        """update the filter preview"""
        try:
            if not hasattr(self, "preview_label") or self.preview_label is None:
                return
            _ = self.preview_label.objectName()
        except RuntimeError:
            return
        preview_parts = []
        raw_preview_parts = []
        
        for i, row in enumerate(self.filter_rows):
            col = row["column"].currentText()
            cond_display = row["condition"].currentText()
            cond = self.ConditionMap.get(cond_display, cond_display)
            val = self.get_current_value(row)

            col_styled = f"<span style='color: #d73a49; font-weight: bold;'>{col}</span>"
            cond_styled = f"<span style='color: #005cc5;'>{cond}</span>"

            part = ""
            raw_part = ""
            if cond in ["Is Null", "Is Not Null"]:
                part = f"{col_styled} {cond_styled}"
                raw_part = f"[{col}] {cond}"
            else:
                val_styled = f"<span style='color: #22863a;'>'{val}'</span>"
                part = f"{col_styled} {cond_styled} {val_styled}"
                raw_part = f"[{col}] {cond} '{val}'"

            if i > 0 and preview_parts:
                logic = row["logic"].currentText()
                logic_styled = f"<span style='color: #6f42c1; font-weight: bold;'>{logic}</span>"
                part = f" {logic_styled} {part}"
                raw_part = f" {logic} {raw_part}"

            preview_parts.append(part)
            raw_preview_parts.append(raw_part)

        text = "".join(preview_parts)
        self._current_raw_query = "".join(raw_preview_parts)
        if text:
            self.preview_label.setText(f"<div style='line-height: 1.4; font-size: 13px;'>{text}</div>")
            self.copy_btn.setVisible(True)
        else:
            self.preview_label.setText("<i>No filters configured</i>")
            self.copy_btn.setVisible(False)

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

        has_validation_error = False
        for row in self.filter_rows:
            cond_display = row["condition"].currentText()
            cond = self.ConditionMap.get(cond_display, cond_display)
            val = self.get_current_value(row)
            if cond not in ["Is Null", "Is Not Null"]:
                if isinstance(val, str) and not val.strip():
                    self._shake_widget(row["inputs"]["text"])
                    has_validation_error = True

        if has_validation_error:
            return

        self._loading_dots = 0
        self.apply_button.setText("Applying")
        self.apply_button.setEnabled(False)
        self.scroll_area.setEnabled(False)
        self._loading_timer.start()
        
        filter_config = self.get_filters()
        
        worker = FilterWorker(self.data_handler, filter_config)
        worker.signals.finished.connect(self.on_filter_finished)
        worker.signals.error.connect(self.on_filter_error)
        self.thread_pool.start(worker)

    def _update_loading_text(self) -> None:
        """Animates an ellipsis on the Apply button to indicate when background worker is active"""
        try:
            self._loading_dots = (self._loading_dots + 1) % 4
            dots = "." * self._loading_dots
            self.apply_button.setText(f"Applying{dots}")
        except RuntimeError:
            self._loading_timer.stop()

    def _shake_widget(self, widget: QWidget) -> None:
        """
        Triggers a horizontal shake to indicate an input error
        """
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(350)
        anim.setEasingCurve(QEasingCurve.Type.OutBounce)

        original_pos = widget.pos()
        anim.setKeyValueAt(0, original_pos)
        anim.setKeyValueAt(0.25, original_pos + QPoint(-5, 0))
        anim.setKeyValueAt(0.5, original_pos + QPoint(5, 0))
        anim.setKeyValueAt(0.75, original_pos + QPoint(-5, 0))
        anim.setKeyValueAt(1.0, original_pos)

        self._active_animations.append(anim)
        anim.finished.connect(lambda: self._active_animations.remove(anim) if anim in self._active_animations else None)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    
    def on_filter_finished(self, result_df):
        self._loading_timer.stop()
        self.apply_button.setText("Apply Filters")
        self.scroll_area.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.data_handler.df = result_df
        self.accept()
    
    def on_filter_error(self, error):
        self._loading_timer.stop()
        self.apply_button.setText("Apply Filters")
        self.scroll_area.setEnabled(True)
        self.apply_button.setEnabled(True)
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