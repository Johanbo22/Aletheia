from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QWidget, QFontComboBox, QAbstractItemView, QColorDialog, QListWidget, QListWidgetItem, QTabWidget
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal

from resources.version import APPLICATION_NAME
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
DEFAULT_GRID_COLOR: str = "#D3D3D3"

class TableCustomizationDialog(QDialog):

    settings_applied = pyqtSignal(dict)
    def __init__(self, current_settings: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Customize data table")
        self.setObjectName("tableCustomizationDialog")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
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
        button_box.accepted.connect(self.apply_settings)
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
        self.grid_check.toggled.connect(self.toggle_grid_controls)
        vbox.addWidget(self.grid_check)

        hbox_grid = QHBoxLayout()
        hbox_grid.setContentsMargins(20, 0, 0, 0)

        self.grid_style_combo = DataPlotStudioComboBox()
        self.grid_style_combo.addItems(["Solid Line", "Dash Line", "Dot Line"])
        self.grid_style_combo.setCurrentText(self.settings.get("grid_style", "Solid Line"))
        hbox_grid.addWidget(self.grid_style_combo)

        self.grid_color_button = DataPlotStudioButton("Grid Color")
        self.grid_color_button.setFixedWidth(100)
        self.current_grid_color = self.settings.get("grid_color", DEFAULT_GRID_COLOR)
        self.grid_color_button.updateColors(self.current_grid_color)
        self.grid_color_button.clicked.connect(self.pick_grid_color)
        hbox_grid.addWidget(self.grid_color_button)
        hbox_grid.addStretch()

        vbox.addLayout(hbox_grid)
        self.toggle_grid_controls(self.grid_check.isChecked())

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
        self.font_combo.setFontFilters(QFontComboBox.FontFilter.ScalableFonts)
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
        self.font_size_spin.setSuffix(" pt")
        hbox_size.addWidget(self.font_size_spin)
        hbox_size.addStretch()
        vbox.addLayout(hbox_size)

        # Font preview
        self.font_preview_label = QLabel(f"{APPLICATION_NAME} 123.45")
        self.font_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.font_preview_label.setFrameShape(QLabel.Shape.StyledPanel)
        self.font_preview_label.setMinimumHeight(45)
        vbox.addWidget(self.font_preview_label)

        self.font_combo.currentFontChanged.connect(self._update_font_preview)
        self.font_size_spin.valueChanged.connect(self._update_font_preview)
        self._update_font_preview()

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

        hbox_nan = QHBoxLayout()
        hbox_nan.addWidget(QLabel("Missing Values (NaN) display:"))
        self.nan_display_combo = DataPlotStudioComboBox()
        self.nan_display_combo.addItems(["<Empty>", "NaN", "N/A", "Null", "-"])
        self.nan_display_combo.setCurrentText(self.settings.get("nan_display", "NaN"))
        hbox_nan.addWidget(self.nan_display_combo)
        hbox_nan.addStretch()
        rep_layout.addLayout(hbox_nan)

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
        self.precision_spin.setSuffix(" decimals")
        hbox_prec.addWidget(self.precision_spin)
        hbox_prec.addStretch()
        precision_layout.addLayout(hbox_prec)

        self.thousands_sep_check = DataPlotStudioToggleSwitch("Use thousands separator (,)")
        self.thousands_sep_check.setChecked(self.settings.get("thousands_separator", False))
        precision_layout.addWidget(self.thousands_sep_check)

        self.scientific_notation_check = DataPlotStudioToggleSwitch("Use scientific notation (e.g., 1.2e+05)")
        self.scientific_notation_check.setChecked(self.settings.get("scientific_notation", False))
        precision_layout.addWidget(self.scientific_notation_check)

        precision_group.setLayout(precision_layout)
        layout.addWidget(precision_group)

        # Conditional formatting options
        conditional_group = DataPlotStudioGroupBox("Conditional Formatting")
        conditional_layout = QVBoxLayout()

        # Rule list
        self.rule_list = DataPlotStudioListWidget()
        self.rule_list.setObjectName("conditionalFormattingList")
        self.rule_list.setToolTip("List of active conditional formatting rules.")
        self.rule_list.setMaximumHeight(120)
        self.rule_list.setAlternatingRowColors(False)

        current_rules = self.settings.get("conditional_rules", [])
        for rule in current_rules:
            self._add_rule_item(rule)

        conditional_layout.addWidget(self.rule_list)

        # Rule controls
        add_rule_layout = QHBoxLayout()
        add_rule_layout.addWidget(QLabel("If value"))
        self.rule_operation_combo = DataPlotStudioComboBox()
        self.rule_operation_combo.addItems(["<", ">", "=", "!=", "<=", ">="])
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

        # Rule management buttons
        rule_btn_layout = QHBoxLayout()

        self.move_up_button = DataPlotStudioButton("Move Up")
        self.move_up_button.setEnabled(False)
        self.move_up_button.setToolTip("Increase the priority of this rule")
        self.move_up_button.clicked.connect(self.move_rule_up)
        rule_btn_layout.addWidget(self.move_up_button)

        self.move_down_button = DataPlotStudioButton("Move Down")
        self.move_down_button.setEnabled(False)
        self.move_down_button.setToolTip("Decrease the priority of this rule.")
        self.move_down_button.clicked.connect(self.move_rule_down)
        rule_btn_layout.addWidget(self.move_down_button)

        self.remove_rule_button = DataPlotStudioButton("Remove")
        self.remove_rule_button.setEnabled(False)
        self.remove_rule_button.clicked.connect(self.remove_rule)
        conditional_layout.addWidget(self.remove_rule_button)

        self.clear_rules_button = DataPlotStudioButton("Clear All")
        self.clear_rules_button.setToolTip("Instantly remove all conditional formatting rules.")
        self.clear_rules_button.setEnabled(len(current_rules) > 0)
        self.clear_rules_button.clicked.connect(self.clear_all_rules)
        rule_btn_layout.addWidget(self.clear_rules_button)

        conditional_layout.addLayout(rule_btn_layout)

        self.rule_list.itemSelectionChanged.connect(self._update_rule_button_state)

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
        behaviors: list[QAbstractItemView.SelectionBehavior] = list(self._selection_mapping.values())
        match_index: int = behaviors.index(current_behavior) if current_behavior in behaviors else 0
        self.selection_behavior_combo.setCurrentIndex(match_index)

        hbox_mode.addWidget(self.selection_behavior_combo)
        vbox.addLayout(hbox_mode)

        selelection_group.setLayout(vbox)
        layout.addWidget(selelection_group)

        layout.addStretch()
        return widget

    def choose_rule_text_color(self):
        """Opens the color dialog for the rules"""
        options = QColorDialog.ColorDialogOption.ShowAlphaChannel
        color = QColorDialog.getColor(QColor(self.rule_color_code), self, "Select Rule Color", options=options)
        if color.isValid():
            self.rule_color_code = color.name(QColor.NameFormat.HexArgb)
            text_color = "black" if color.lightness() > 128 else "white"
            self.rule_color_button.updateColors(base_color_hex=self.rule_color_code, text_color_hex=text_color)

    def choose_rule_bg_color(self) -> None:
        """Opens the color dialog for the rule background color"""
        options = QColorDialog.ColorDialogOption.ShowAlphaChannel
        color = QColorDialog.getColor(QColor(self.rule_bg_color_code), self, "Select Rule Background Color", options=options)
        if color.isValid():
            self.rule_bg_color_code = color.name(QColor.NameFormat.HexArgb)
            text_color = "black" if color.lightness() > 128 else "white"
            self.rule_bg_color_button.updateColors(base_color_hex=self.rule_bg_color_code, text_color_hex=text_color)

    def _update_font_preview(self) -> None:
        """Updates the font preview label based on the selected font settings"""
        font: QFont = self.font_combo.currentFont()
        font.setPointSize(self.font_size_spin.value())
        self.font_preview_label.setFont(font)

    def _update_rule_button_state(self) -> None:
        """Enables or disables rule buttons based on selection and list boundaries"""
        selected_items = self.rule_list.selectedItems()
        has_selection: bool = bool(selected_items)
        self.remove_rule_button.setEnabled(has_selection)

        row: int = self.rule_list.currentRow()
        self.move_up_button.setEnabled(has_selection and row > 0)
        self.move_down_button.setEnabled(has_selection and row < self.rule_list.count() - 1 and row >= 0)

        if has_selection:
            rule_data: dict | None = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if rule_data:
                self.rule_operation_combo.setCurrentText(rule_data.get("operator", "="))
                self.rule_value_spin.setValue(float(rule_data.get("value", 0.0)))

                self.rule_color_code = rule_data.get("color", DEFAULT_RULE_TEXT_COLOR)
                text_fg: str = "black" if QColor(self.rule_color_code).lightness() > 128 else "white"
                self.rule_color_button.updateColors(base_color_hex=self.rule_color_code, text_color_hex=text_fg)

                self.rule_bg_color_code = rule_data.get("bg_color", DEFAULT_RULE_BG_COLOR)
                bg_fg: str = "black" if QColor(self.rule_bg_color_code).lightness() > 128 else "white"
                self.rule_bg_color_button.updateColors(base_color_hex=self.rule_bg_color_code, text_color_hex=bg_fg)

    def move_rule_up(self) -> None:
        """Moves the selected formatting rule up in priority"""
        row: int = self.rule_list.currentRow()
        if row > 0:
            item: QListWidgetItem = self.rule_list.takeItem(row)
            self.rule_list.insertItem(row - 1, item)
            self.rule_list.setCurrentRow(row - 1)

    def move_rule_down(self) -> None:
        """Moves the selected formatting rule down in priority"""
        row: int = self.rule_list.currentRow()
        if 0 <= row < self.rule_list.count() - 1:
            item: QListWidgetItem = self.rule_list.takeItem(row)
            self.rule_list.insertItem(row + 1, item)
            self.rule_list.setCurrentRow(row + 1)

    def add_rule(self):
        """Adds new rule to the list. Updates existing rule if operator and value match"""
        operator: str = self.rule_operation_combo.currentText()
        value: float = self.rule_value_spin.value()

        rule: dict = {
            "operator": self.rule_operation_combo.currentText(),
            "value": self.rule_value_spin.value(),
            "color": self.rule_color_code,
            "bg_color": self.rule_bg_color_code
        }

        # To prevent duplicate entries
        # Update colors if an identical rule already exists in list
        for i in range(self.rule_list.count()):
            item: QListWidgetItem = self.rule_list.item(i)
            existing_rule: dict | None = item.data(Qt.ItemDataRole.UserRole)

            if existing_rule and existing_rule.get("operator") == operator and existing_rule.get("value") == value:
                item.setData(Qt.ItemDataRole.UserRole, rule)

                text_color: QColor = QColor(self.rule_color_code)
                if text_color.isValid():
                    item.setForeground(text_color)

                bg_color: QColor = QColor(self.rule_bg_color_code)
                if bg_color.isValid():
                    item.setBackground(bg_color)

                self.rule_list.clearSelection()
                return

        self._add_rule_item(rule)

    def _add_rule_item(self, rule: dict) -> None:
        """
        Creates a list widget item from the dictionary of added rules
        Applies the selected colors to the item itself to serve as live visual of the rule
        """
        text: str = f"If value {rule["operator"]} {rule["value"]}"
        item = QListWidgetItem(text)

        text_color: QColor = QColor(rule.get("color", DEFAULT_RULE_TEXT_COLOR))
        if text_color.isValid():
            item.setForeground(text_color)

        bg_color_hex: str | None = rule.get("bg_color")
        if bg_color_hex:
            bg_color: QColor = QColor(bg_color_hex)
            if bg_color.isValid():
                item.setBackground(bg_color)

        font: QFont = item.font()
        font.setBold(True)
        item.setFont(font)

        item.setData(Qt.ItemDataRole.UserRole, rule)
        self.rule_list.addItem(item)

    def remove_rule(self):
        """Removes the selected rule from the list and updates the selection"""
        row: int = self.rule_list.currentRow()
        if row >= 0:
            self.rule_list.takeItem(row)

            new_count: int = self.rule_list.count()
            if new_count > 0:
                next_row: int = min(row, new_count - 1)
                self.rule_list.setCurrentRow(next_row)
            else:
                self.rule_list.clearSelection()
                self.clear_rules_button.setEnabled(False)

    def clear_all_rules(self) -> None:
        """Instantly clears all formatting rules"""
        self.rule_list.clear()
        self.rule_list.clearSelection()
        self.clear_rules_button.setEnabled(False)

    def toggle_alt_color_button(self, checked: bool):
        self.alt_color_button.setEnabled(checked)

    def toggle_grid_controls(self, checked: bool) -> None:
        """Enables or disables grid styling controls based on toggle of grids"""
        self.grid_style_combo.setEnabled(checked)
        self.grid_color_button.setEnabled(checked)

    def pick_grid_color(self) -> None:
        options = QColorDialog.ColorDialogOption.ShowAlphaChannel
        color: QColor = QColorDialog.getColor(QColor(self.current_grid_color), self, "Select Grid Line Color", options=options)
        if color.isValid():
            self.current_grid_color = color.name(QColor.NameFormat.HexArgb)
            self.grid_color_button.updateColors(self.current_grid_color)

    def pick_alt_color(self):
        options = QColorDialog.ColorDialogOption.ShowAlphaChannel
        color: QColor = QColorDialog.getColor(QColor(self.current_alt_color), self, "Select Alternating Row Color",options=options)
        if color.isValid():
            self.current_alt_color = color.name(QColor.NameFormat.HexArgb)
            self.alt_color_button.updateColors(self.current_alt_color)

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
            "grid_color": self.current_grid_color,
            "grid_style": self.grid_style_combo.currentText(),
            "show_h_headers": self.horizontal_header_check.isChecked(),
            "show_v_headers": self.vertical_header_check.isChecked(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.font_size_spin.value(),
            "word_wrap": self.word_wrap_check.isChecked(),
            "selection_behavior": selection_behavior,
            "float_precision": self.precision_spin.value(),
            "thousands_separator": self.thousands_sep_check.isChecked(),
            "scientific_notation": self.scientific_notation_check.isChecked(),
            "nan_display": self.nan_display_combo.currentText(),
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
        self.alt_color_button.setEnabled(True)

        self.grid_check.setChecked(True)
        self.current_grid_color = DEFAULT_GRID_COLOR
        self.grid_color_button.updateColors(self.current_grid_color)
        self.grid_style_combo.setCurrentText("Solid Line")
        self.toggle_grid_controls(True)

        self.horizontal_header_check.setChecked(True)
        self.vertical_header_check.setChecked(True)

        self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
        self.word_wrap_check.setChecked(False)
        self.alignment_combo.setCurrentText("Left")

        self.render_bools_check.setChecked(True)
        self.nan_display_combo.setCurrentText("NaN")

        self.precision_spin.setValue(DEFAULT_FLOAT_PRECISION)
        self.thousands_sep_check.setChecked(False)
        self.scientific_notation_check.setChecked(False)

        self.rule_list.clear()

        self.rule_operation_combo.setCurrentIndex(0)
        self.rule_value_spin.setValue(0.0)

        self.rule_color_code = DEFAULT_RULE_TEXT_COLOR
        self.rule_color_button.updateColors(base_color_hex=self.rule_color_code)

        self.rule_bg_color_code = DEFAULT_RULE_BG_COLOR
        self.rule_bg_color_button.updateColors(base_color_hex=self.rule_bg_color_code)

        self.clear_rules_button.setEnabled(False)
        self.selection_behavior_combo.setCurrentText("Select Items")