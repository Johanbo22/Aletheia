from typing import Dict, Any

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from ui.dialogs.FilterAdvancedDialog import FilterAdvancedDialog
from ui.widgets.ControlElements import DataPlotStudioLineEdit


class CreateSubsetDialog(FilterAdvancedDialog):
    """Dialog for creating and editing subsets"""
    
    def __init__(self, data_handler, parent=None, existing_subset=None) -> None:
        self.existing_subset = existing_subset

        super().__init__(data_handler, parent)

        self.setWindowTitle("Create Subset" if not existing_subset else "Edit Subset")
        self.resize(900, 750)

        self._augment_ui()

        if existing_subset:
            self.load_existing_subset()

    def _augment_ui(self) -> None:
        """Adding extra UI for subset such as Name and description boxes"""
        main_layout = self.layout()

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        if not self.existing_subset:
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Subset Name:"))
            self.name_input = DataPlotStudioLineEdit()
            self.name_input.setPlaceholderText("e.g., high_values, location_A, etc")
            name_layout.addWidget(self.name_input)
            top_layout.addLayout(name_layout)

        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = DataPlotStudioLineEdit()
        self.desc_input.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_input)
        top_layout.addLayout(desc_layout)

        main_layout.insertWidget(0, top_widget)

        self.apply_button.setText("Create" if not self.existing_subset else "Update")
        self.apply_button.setToolTip("Save this subset configuration")

    def validate_and_accept(self) -> None:
        """Overrides parent class method to validate subset metadata before accepting."""
        if not self.existing_subset:
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Validation Error", "Please enter a subset name")
                return

        if not self.filter_rows:
            QMessageBox.warning(self, "Validation Error", "Please create at least one filter")
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
            QMessageBox.warning(self, "Validation Error", "Please enter values for all active filters")
            return
        self.accept()

    def load_existing_subset(self) -> None:
        """Load an existing subset into the form"""
        self.desc_input.setText(self.existing_subset.description)

        filters = getattr(self.existing_subset, "filters", [])
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

    def get_config(self) -> Dict[str, Any]:
        """Returns the subset config"""
        config = self.get_filters()

        config["description"] = self.desc_input.text().strip()
        if not self.existing_subset:
            config["name"] = self.name_input.text().strip()

        return config