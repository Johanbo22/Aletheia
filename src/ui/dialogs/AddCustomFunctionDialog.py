from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.core.global_signals import ToastLevel, global_signals
from src.ui.widgets.CodeEditor import CodeEditor

class AddCustomFunctionDialog(QDialog):
    """
    A dialog for defining and saving custom expression snippets
    These expressions snippets can then be used in the ComputeColumnDialog
    """

    def __init__(self, existing_categories: list[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.existing_categories = existing_categories or []
        self.setWindowTitle("Add Custom Function")
        self.setMinimumWidth(450)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Function name
        layout.addWidget(QLabel("Function Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Percentage Difference")
        self.name_input.setToolTip("A recognizable name for your custom function")
        layout.addWidget(self.name_input)

        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.setPlaceholderText("e.g., Custom Math")
        self.category_input.setToolTip(
            "Group your custom functions. You can type a new group or select an existing one")
        self.category_input.addItems(self.existing_categories)
        layout.addWidget(self.category_input)

        # Description / Tooltip role for the custom function
        description_layout = QHBoxLayout()
        description_layout.setContentsMargins(0, 0, 0, 0)
        description_layout.setSpacing(6)

        description_label = QLabel("Description")
        optional_badge = QLabel("Optional")
        optional_badge.setProperty("styleClass", "optional_badge")

        description_layout.addWidget(description_label)
        description_layout.addWidget(optional_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        description_layout.addStretch()
        layout.addLayout(description_layout)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("e.g., Calculates (A - B) / A")
        self.desc_input.setToolTip("Will be displayed when hovering over the function in the function tree")
        layout.addWidget(self.desc_input)

        # Snippet editor
        layout.addWidget(QLabel("Code Snippet:"))
        self.snippet_input = CodeEditor()
        self.snippet_input.setObjectName("computed_column_expression")
        self.snippet_input.setPlaceholderText("e.g., (`Target` - `Actual`) / `Target`")
        self.snippet_input.setToolTip("The string to be inserted into the expression editor")
        self.snippet_input.setMinimumHeight(120)
        layout.addWidget(self.snippet_input)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save Custom Function")
        self.save_button.setObjectName("MainActionButton")
        self.save_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def validate_and_accept(self) -> None:
        """Validates the inputs before accepting the dialog"""
        if not self.name_input.text().strip():
            global_signals.request_toast("Validation Error", "Please provide a valid Function name", ToastLevel.WARNING)
            self.name_input.setFocus()
            return
        if not self.snippet_input.toPlainText().strip():
            global_signals.request_toast("Validation Error", "The code snippet cannot be empty", ToastLevel.WARNING)
            self.snippet_input.setFocus()
            return
        self.accept()

    def get_function_data(self) -> tuple[str, str, str, str]:
        """
        Retrieves the configured custom function data

        Returns:
            tuple[str, str, str]: (name, category, description, snippet)
        """
        category = self.category_input.currentText().strip()
        if not category:
            category = "Custom Functions"
        return (
            self.name_input.text().strip(),
            category,
            self.desc_input.text().strip(),
            self.snippet_input.toPlainText().strip()
        )
