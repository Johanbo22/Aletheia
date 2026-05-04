from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QWidget, QFontComboBox, QAbstractItemView, QColorDialog, QListWidget, QListWidgetItem, QTabWidget
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal

from ui.widgets import DataPlotStudioButton, DataPlotStudioToggleSwitch
from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioListWidget, DataPlotStudioSpinBox

DIALOG_WIDTH: int = 600
DIALOG_HEIGHT: int = 500
MIN_FONT_SIZE: int = 6
MAX_FONT_SIZE: int = 72
DEFAULT_FONT_SIZE: int = 10
DEFAULT_FLOAT_PRECISION: int = 2
MIN_FLOAT_PRECISION: int = 0
MAX_FLOAT_PRECISION: int = 10
MIN_RULE_VALUE: float = -9999999.0
MAX_RULE_VALUE: float = 9999999.0
DEFAULT_RULE_TEXT_COLOR: str = "#FF0000"
DEFAULT_RULE_BG_COLOR: str = "#FFFFFF"
DEFAULT_ALT_COLOR: str = "#F5F5F5"

class TableCustomizationDialog(QDialog):
    
    settings_applied = pyqtSignal(dict)
    def __init__(self, current_settings: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Customize data table")
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.settings = current_settings or {}
        
        self._selection_mapping = {
            "Select Items": QAbstractItemView.SelectionBehavior.SelectItems,
            "Select Rows": QAbstractItemView.SelectionBehavior.SelectRows,
            "Select Columns": QAbstractItemView.SelectionBehavior.SelectColumns
        }
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_appearance_tab(), "Appearance")
        self.tabs.addTab(self.create_font_tab(), "Font and Text")
        self.tabs.addTab(self.create_formatting_tab(), "Formatting")
        self.tabs.addTab(self.create_behavior_tab(), "Behavior")

        main_layout.addWidget(self.tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        apply_btn = button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn:
            apply_btn.clicked.connect(self.apply_settings)
        
        restore_btn = button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if restore_btn:
            restore_btn.clicked.connect(self.reset_to_defaults)
            
        main_layout.addWidget(button_box)
    
    def create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # General settings
        group = DataPlotStudioGroupBox("General")
        vbox = QVBoxLayout()

        hbox_alt = QHBoxLayout()
        self.alternating_check = DataPlotStudioToggleSwitch("Alternating Row Colors")
        self.alternating_check.setChecked(self.settings.get("alternating_rows", True))
        self.alternating_check.toggled.connect(self.toggle_alt_color_button)
        vbox.addWidget(self.alternating_check)

        self.alt_color_button = DataPlotStudioButton("Choose Color")
        self.alt_color_button.setFixedWidth(140)
        self.alt_color_button.setToolTip("Click to change the color of the alternating row")
        self.current_alt_color = self.settings.get("alt_color", DEFAULT_ALT_COLOR)
        self.alt_color_button.updateColors(self.current_alt_color)
        self.alt_color_button.clicked.connect(self.pick_alt_color)

        hbox_alt.addWidget(self.alt_color_button)
        hbox_alt.addStretch()

        vbox.addLayout(hbox_alt)

        self.toggle_alt_color_button(self.alternating_check.isChecked())

        self.grid_check = DataPlotStudioToggleSwitch("Show Grid Lines")
        self.grid_check.setChecked(self.settings.get("show_grid", True))
        vbox.addWidget(self.grid_check)

        group.setLayout(vbox)
        layout.addWidget(group)

        # Headers
        header_group = DataPlotStudioGroupBox("Headers")
        header_vbox = QVBoxLayout()

        self.horizontal_header_check = DataPlotStudioToggleSwitch("Show Horizontal Headers")
        self.horizontal_header_check.setChecked(self.settings.get("show_h_headers", True))
        header_vbox.addWidget(self.horizontal_header_check)

        self.vertical_header_check = DataPlotStudioToggleSwitch("Show Vertical Headers (Index)")
        self.vertical_header_check.setChecked(self.settings.get("show_v_header", True))
        header_vbox.addWidget(self.vertical_header_check)

        header_group.setLayout(header_vbox)
        layout.addWidget(header_group)

        layout.addStretch()
        return widget
    
    def create_font_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        font_group = DataPlotStudioGroupBox("Table Font")
        vbox = QVBoxLayout()

        # Font Family of the data table
        hbox_family = QHBoxLayout()
        hbox_family.addWidget(QLabel("Font Family:"))
        self.font_combo = QFontComboBox()
        current_font = self.settings.get("font_family")
        if current_font:
            self.font_combo.setCurrentFont(QFont(current_font))
        hbox_family.addWidget(self.font_combo, 1)
        vbox.addLayout(hbox_family)

        # Font size
        hbox_size = QHBoxLayout()
        hbox_size.addWidget(QLabel("Font Size:"))
        self.font_size_spin = DataPlotStudioSpinBox()
        self.font_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.font_size_spin.setValue(self.settings.get("font_size", DEFAULT_FONT_SIZE))
        hbox_size.addWidget(self.font_size_spin)
        hbox_size.addStretch()
        vbox.addLayout(hbox_size)

        font_group.setLayout(vbox)
        layout.addWidget(font_group)

        # Text Options
        text_group = DataPlotStudioGroupBox("Text Display")
        text_vbox = QVBoxLayout()

        self.word_wrap_check = DataPlotStudioToggleSwitch("Word Wrap Long Text")
        self.word_wrap_check.setChecked(self.settings.get("word_wrap", False))
        text_vbox.addWidget(self.word_wrap_check)
        
        # Text alignment options
        hbox_align = QHBoxLayout()
        hbox_align.addWidget(QLabel("Default Alignment:"))
        self.alignment_combo = DataPlotStudioComboBox()
        self.alignment_combo.addItems(["Left", "Center", "Right"])
        
        current_alignment = self.settings.get("text_alignment", "Left")
        self.alignment_combo.setCurrentText(current_alignment)
        hbox_align.addWidget(self.alignment_combo)
        
        text_vbox.addLayout(hbox_align)

        text_group.setLayout(text_vbox)
        layout.addWidget(text_group)

        layout.addStretch()
        return widget
    
    def create_formatting_tab(self) -> QWidget:
        """Creates the tab with numerical and conditional formatting options"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data representation group
        representation_group = DataPlotStudioGroupBox("Data Representation")
        rep_layout = QVBoxLayout()
        
        self.render_bools_check = DataPlotStudioToggleSwitch("Render Booleans as checkboxes")
        self.render_bools_check.setChecked(self.settings.get("render_bools_as_checkboxes", True))
        self.render_bools_check.setToolTip("Toggle to display boolean values as a checkbox or standard text")
        rep_layout.addWidget(self.render_bools_check)
        
        representation_group.setLayout(rep_layout)
        layout.addWidget(representation_group)
        
        # Floating point precision options
        precision_group = DataPlotStudioGroupBox("Floating Point Precision")
        precision_layout = QVBoxLayout()
        
        hbox_prec = QHBoxLayout()
        hbox_prec.addWidget(QLabel("Float Decimal Places:"))
        self.precision_spin = DataPlotStudioSpinBox()
        self.precision_spin.setRange(MIN_FLOAT_PRECISION, MAX_FLOAT_PRECISION)
        self.precision_spin.setValue(self.settings.get("float_precision", DEFAULT_FLOAT_PRECISION))
        self.precision_spin.setToolTip("Set the number of decimal places to display for floating point numbers.")
        hbox_prec.addWidget(self.precision_spin)
        hbox_prec.addStretch()
        
        precision_layout.addLayout(hbox_prec)
        precision_group.setLayout(precision_layout)
        layout.addWidget(precision_group)
        
        # Conditional formatting options
        conditional_group = DataPlotStudioGroupBox("Conditional Formatting")
        conditional_layout = QVBoxLayout()
        
        # Rule list
        self.rule_list = DataPlotStudioListWidget()
        self.rule_list.setToolTip("List of active conditional formatting rules.")
        self.rule_list.setMaximumHeight(120)
        
        current_rules = self.settings.get("conditional_rules", [])
        for rule in current_rules:
            self._add_rule_item(rule)
        
        conditional_layout.addWidget(self.rule_list)
        
        # Rule controls
        add_rule_layout = QHBoxLayout()
        add_rule_layout.addWidget(QLabel("If value"))
        self.rule_operation_combo = DataPlotStudioComboBox()
        self.rule_operation_combo.addItems(["<", ">", "=", "<=", ">="])
        self.rule_operation_combo.setFixedWidth(60)
        add_rule_layout.addWidget(self.rule_operation_combo)
        
        self.rule_value_spin = DataPlotStudioDoubleSpinBox()
        self.rule_value_spin.setRange(MIN_RULE_VALUE, MAX_RULE_VALUE)
        self.rule_value_spin.setDecimals(DEFAULT_FLOAT_PRECISION)
        self.rule_value_spin.setFixedWidth(100)
        add_rule_layout.addWidget(self.rule_value_spin)
        
        # Text color picker
        self.rule_color_button = DataPlotStudioButton("Text")
        self.rule_color_button.setFixedWidth(60)
        self.rule_color_code = DEFAULT_RULE_TEXT_COLOR
        self.rule_color_button.updateColors(base_color_hex=self.rule_color_code, text_color_hex="white")
        self.rule_color_button.clicked.connect(self.choose_rule_text_color)
        add_rule_layout.addWidget(self.rule_color_button)
        
        # Background color picker
        self.rule_bg_color_button = DataPlotStudioButton("Fill")
        self.rule_bg_color_button.setFixedWidth(50)
        self.rule_bg_color_code = DEFAULT_RULE_BG_COLOR
        self.rule_bg_color_button.updateColors(base_color_hex=self.rule_bg_color_code, text_color_hex="black")
        self.rule_bg_color_button.clicked.connect(self.choose_rule_bg_color)
        add_rule_layout.addWidget(self.rule_bg_color_button)
        
        add_rule_button = DataPlotStudioButton("Add Rule")
        add_rule_button.setToolTip("Add this conditional formatting fule.")
        add_rule_button.clicked.connect(self.add_rule)
        add_rule_layout.addWidget(add_rule_button)
        
        conditional_layout.addLayout(add_rule_layout)
        
        # Remove rules button
        remove_rule_button = DataPlotStudioButton("Remove Selected Rule")
        remove_rule_button.clicked.connect(self.remove_rule)
        conditional_layout.addWidget(remove_rule_button)
        
        conditional_group.setLayout(conditional_layout)
        layout.addWidget(conditional_group)
        
        layout.addStretch()
        return widget
    
    def create_behavior_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        selelection_group = DataPlotStudioGroupBox("Selection Mode")
        vbox = QVBoxLayout()

        hbox_mode = QHBoxLayout()
        hbox_mode.addWidget(QLabel("Selection Behavior:"))
        self.selection_behavior_combo = DataPlotStudioComboBox()
        self.selection_behavior_combo.addItems(list(self._selection_mapping.keys()))

        # those settings are mapped to index
        current_behavior = self.settings.get("selection_behavior", QAbstractItemView.SelectionBehavior.SelectItems)
        match_index = 0
        for index, behavior in enumerate(self._selection_mapping.values()):
            if behavior == current_behavior:
                match_index = index
                break
        self.selection_behavior_combo.setCurrentIndex(match_index)
        
        hbox_mode.addWidget(self.selection_behavior_combo)
        vbox.addLayout(hbox_mode)

        selelection_group.setLayout(vbox)
        layout.addWidget(selelection_group)

        layout.addStretch()
        return widget
    
    def choose_rule_text_color(self):
        """Opens the color dialog for the rules"""
        color = QColorDialog.getColor(QColor(self.rule_color_code), self, "Select Rule Color")
        if color.isValid():
            self.rule_color_code = color.name()
            text_color = "black" if color.lightness() > 128 else "white"
            self.rule_color_button.updateColors(base_color_hex=self.rule_color_code, text_color_hex=text_color)
    
    def choose_rule_bg_color(self) -> None:
        """Opens the color dialog for the rule background color"""
        color = QColorDialog.getColor(QColor(self.rule_bg_color_code), self, "Select Rule Background Color")
        if color.isValid():
            self.rule_bg_color_code = color.name()
            text_color = "black" if color.lightness() > 128 else "white"
            self.rule_bg_color_button.updateColors(base_color_hex=self.rule_bg_color_code, text_color_hex=text_color)
    
    def add_rule(self):
        """Adds new rule to the list"""
        rule = {
            "operator": self.rule_operation_combo.currentText(),
            "value": self.rule_value_spin.value(),
            "color": self.rule_color_code,
            "bg_color": self.rule_bg_color_code
        }
        self._add_rule_item(rule)
    
    def _add_rule_item(self, rule: dict):
        """Creates a list widget item from the dictionary of added rules"""
        text = f"If value {rule['operator']} {rule['value']} -> Text: {rule['color']} | Fill: {rule.get('bg_color', 'None')}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, rule)
        self.rule_list.addItem(item)
    
    def remove_rule(self):
        """Removes the selected rule from the list"""
        row = self.rule_list.currentRow()
        if row >= 0:
            self.rule_list.takeItem(row)
    
    def toggle_alt_color_button(self, checked: bool):
        self.alt_color_button.setEnabled(checked)

    def pick_alt_color(self):
        color = QColorDialog.getColor(QColor(self.current_alt_color), self, "Select Alternating Row Color")
        if color.isValid():
            self.current_alt_color = color.name()

    def get_settings(self) -> dict:
        """Configured settings"""
        selection_text = self.selection_behavior_combo.currentText()
        selection_behavior = self._selection_mapping.get(selection_text, QAbstractItemView.SelectionBehavior.SelectItems)
        
        # Retrieve rules
        conditional_rules = []
        for i in range(self.rule_list.count()):
            item = self.rule_list.item(i)
            rule_data = item.data(Qt.ItemDataRole.UserRole)
            if rule_data:
                conditional_rules.append(rule_data)
                
        return {
            "alternating_rows": self.alternating_check.isChecked(),
            "alt_color": self.current_alt_color,
            "show_grid": self.grid_check.isChecked(),
            "show_h_headers": self.horizontal_header_check.isChecked(),
            "show_v_headers": self.vertical_header_check.isChecked(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.font_size_spin.value(),
            "word_wrap": self.word_wrap_check.isChecked(),
            "selection_behavior": selection_behavior,
            "float_precision": self.precision_spin.value(),
            "conditional_rules": conditional_rules,
            "text_alignment": self.alignment_combo.currentText(),
            "render_bools_as_checkboxes": self.render_bools_check.isChecked()
        }
    
    def apply_settings(self) -> None:
        """Emits the current settings without closing the dialog"""
        current_config = self.get_settings()
        self.settings_applied.emit(current_config)
    
    def reset_to_defaults(self) -> None:
        """Resets the UI components to system standard defaults."""
        self.alternating_check.setChecked(True)
        self.current_alt_color = DEFAULT_ALT_COLOR
        self.alt_color_button.updateColors(self.current_alt_color)
        
        self.grid_check.setChecked(True)
        self.horizontal_header_check.setChecked(True)
        self.vertical_header_check.setChecked(True)
        
        self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
        self.word_wrap_check.setChecked(False)
        self.alignment_combo.setCurrentText("Left")
        
        self.render_bools_check.setChecked(True)
        self.precision_spin.setValue(DEFAULT_FLOAT_PRECISION)
        self.rule_list.clear()
        
        self.selection_behavior_combo.setCurrentText("Select Items")