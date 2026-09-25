import re
from typing import List, Optional, Tuple

from PyQt6.QtWidgets import QDialog

from src.ui.dialogs.RenameColumnDialog import RenameColumnDialog, ValidationState

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}

class RenameProjectDialog(RenameColumnDialog):
    """Dialog for renaming a project on disk"""

    def __init__(self, current_name: str, existing_names: Optional[List[str]] = None,
                 parent: Optional[QDialog] = None) -> None:
        super().__init__(current_name, existing_columns=existing_names, parent=parent)
        self.setWindowTitle("Rename Project")
        self.case_sensitive: bool = False
        self.new_name_input.setText(self.column_name)
        self.new_name_input.selectAll()

    def validate_name(self, new_name: str) -> Tuple[ValidationState, str]:
        if not new_name:
            return ValidationState.Empty, "New project name cannot be empty"
        if self._same_as_current(new_name):
            return ValidationState.Unchanged, "New name must be different from current name"
        if self._already_exists(new_name):
            return ValidationState.AlreadyExists, f"A project named '{new_name}' already exists in this folder"
        if new_name.upper() in _RESERVED_NAMES or new_name.rstrip(".") != new_name or new_name.rstrip() != new_name:
            return ValidationState.InvalidCharacter, f"'{new_name}' is not a valid file name"
        if _INVALID_FILENAME_CHARS.search(new_name):
            return ValidationState.InvalidCharacter, r'Project names cannot contain \ / : * ? " < > |'

        return ValidationState.Valid, ""
