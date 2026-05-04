import json
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox, QListWidgetItem, QWidget, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, QSize

from ui.widgets import DataPlotStudioButton, DataPlotStudioToggleSwitch
from ui.icons import IconBuilder, IconType
from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioListWidget

class MacroPreviewDialog(QDialog):
    """
    Dialog to preview the sequence of data operations contained
    in a JSON macro before applying them to the dataset
    """
    
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.step_trackers = []
        self.setWindowTitle("Preview Data Pipeline Macro")
        self.resize(750, 650)
        self.init_ui()
        self.load_macro_preview()
    
    def init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_icon = QLabel()
        try:
            header_icon.setPixmap(IconBuilder.build(IconType.DataTransform).pixmap(32, 32))
        except Exception:
            pass
        
        filename = Path(self.filepath).name
        
        info_label = QLabel(f"<b>Previewing Macro:</b><br>{filename}<br><br>The following operations will be applied in sequence:")
        info_label.setToolTip(self.filepath)
        info_label.setWordWrap(True)
        info_label.setProperty("styleClass", "h2")
        
        header_layout.addWidget(header_icon)
        header_layout.addWidget(info_label, stretch=1)
        self.main_layout.addLayout(header_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(line)
        
        util_layout = QHBoxLayout()
        self.toggle_all_btn = DataPlotStudioButton("Deselect All")
        self.toggle_all_btn.setCheckable(True)
        self.toggle_all_btn.setChecked(True)
        self.toggle_all_btn.clicked.connect(self._toggle_all_checkboxes)
        self.toggle_all_btn.setProperty("styleClass", "secondary_button")
        
        util_layout.addWidget(QLabel("<b>Execution Sequence</b>"))
        util_layout.addStretch()
        util_layout.addWidget(self.toggle_all_btn)
        self.main_layout.addLayout(util_layout)
        
        self.operations_list = DataPlotStudioListWidget()
        self.operations_list.setAlternatingRowColors(True)
        self.operations_list.setSelectionMode(DataPlotStudioListWidget.SelectionMode.NoSelection)
        self.operations_list.setSpacing(2)
        self.main_layout.addWidget(self.operations_list)
        
        self.summary_label = QLabel("Total steps: 0")
        self.summary_label.setProperty("styleClass", "muted_text")
        self.main_layout.addWidget(self.summary_label)
        
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        )
        apply_btn = self.button_box.button(QDialogButtonBox.StandardButton.Apply)
        apply_btn.setText("Execute Macro")
        apply_btn.setIcon(IconBuilder.build(IconType.Checkmark))
        apply_btn.clicked.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        self.main_layout.addWidget(self.button_box)
        
    def _create_item_widget(self, index: int, op_type: str, params_str: str, is_skipped: bool) -> tuple[QWidget, DataPlotStudioCheckBox]:
        """Creates a custom widget for a single macro operation"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        checkbox = DataPlotStudioCheckBox()
        checkbox.setChecked(not is_skipped)
        if is_skipped:
            checkbox.setEnabled(False)
            checkbox.setToolTip("This operation type is not supported in macros.")
        layout.addWidget(checkbox)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(f"<b>{index}. {op_type}</b>")
        if is_skipped:
            title_label.setText(f"<s>{title_label.text()}</s> <span style='color:#d9534f;'>(Unsupported)</span>")
            
        text_layout.addWidget(title_label)
        
        param_label = QLabel(params_str)
        param_label.setWordWrap(True)
        param_label.setProperty("styleClass", "muted_text")
        
        font = param_label.font()
        font.setPointSize(font.pointSize() - 1)
        param_label.setFont(font)
        
        if is_skipped:
            param_label.setStyleSheet("color: gray;")
            
        text_layout.addWidget(param_label)
        layout.addLayout(text_layout, stretch=1)
        
        checkbox.toggled.connect(self._update_summary_footer)
        
        return widget, checkbox
    
    def load_macro_preview(self) -> None:
        """
        Reads the JSON file and populates the
        list widget with formatted steps
        """
        try:
            with open(self.filepath, 'r') as f:
                operations = json.load(f)
            
            if not isinstance(operations, list):
                self._add_error_message("Invalid macro format: Expected a list of operations.")
                return
                
            if not operations:
                self._add_error_message("Macro is empty.")
                return
                
            for index, op in enumerate(operations, start=1):
                raw_op_type = op.get("type", "Unknown Operation")
                op_title = raw_op_type.replace("_", " ").title()
                
                params = [f"<b>{k}</b>: {v}" for k, v in op.items() if k != "type"]
                params_str = " | ".join(params) if params else "No parameters required"
                
                is_skipped = raw_op_type in ["merge", "concatenate", "export_google_sheets"]
                
                item_widget, checkbox = self._create_item_widget(index, op_title, params_str, is_skipped)
                self.step_trackers.append((checkbox, op))
                
                item = QListWidgetItem(self.operations_list)
                item.setSizeHint(item_widget.sizeHint() + QSize(0, 5))
                self.operations_list.addItem(item)
                self.operations_list.setItemWidget(item, item_widget)
                
            self._update_summary_footer()
                
        except Exception as err:
            self._add_error_message(f"Failed to parse macro file:\n{str(err)}")
    
    def _update_summary_footer(self) -> None:
        """
        Updates the footer text to reflect
        how many steps are targeted for execution
        """
        total = len(self.step_trackers)
        selected = sum(1 for cb, _ in self.step_trackers if cb.isChecked())
        skipped_hard = sum(1 for cb, _ in self.step_trackers if not cb.isEnabled())
        
        summary_text = f"Operations to execute: <b>{selected} / {total}</b>"
        if skipped_hard > 0:
            summary_text += f" &nbsp;|&nbsp; <span style='color:#d9534f;'><b>{skipped_hard} unsupported</b></span>"
        
        self.summary_label.setText(summary_text)
        
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(selected > 0)
    
    def _toggle_all_checkboxes(self) -> None:
        target_state = self.toggle_all_btn.isChecked()
        self.toggle_all_btn.setText("Deselect All" if target_state else "Select All")
        
        for cb, _ in self.step_trackers:
            if cb.isEnabled():
                cb.setChecked(target_state)
    
    def get_selected_operations(self) -> list:
        """
        Returns a list of operations dictionaries
        that were checked 
        """
        return [op_dict for cb, op_dict in self.step_trackers if cb.isChecked()]
    
    def _add_error_message(self, message: str) -> None:
        self.operations_list.clear()
        item = QListWidgetItem(message)
        self.operations_list.addItem(item)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)
        self.summary_label.setText("Error loading macro")