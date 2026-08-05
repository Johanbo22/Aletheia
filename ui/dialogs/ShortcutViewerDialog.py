import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem, QVBoxLayout, QWidget

class ShortcutViewerDialog(QDialog):
    """
    A non-modal floating tool window displaying the keyboard shortcuts and mouse interactions
    for the PlotStudio interface
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard & Mouse Shortcuts")

        self.setWindowFlags(Qt.WindowType.Tool)
        self.setModal(False)
        self.setMinimumSize(450, 400)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.is_mac: bool = sys.platform == "darwin"

        self._setup_ui()
        self._populate_shortcuts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search shortcuts by name or key...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_shortcuts)
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Interaction", "Shortcut"])

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setObjectName("MainDataHeader")
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("MainActionButton")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _get_shortcut_data(self) -> list[tuple[str, str, str]]:
        """
        Gets the standard shortcuts based on the os
        :return: A list of tuples containing (Name, Key/action, description)
        """
        ctrl = "⌘" if self.is_mac else "Ctrl"
        return [
            ("Generate Plot", f"{ctrl} + Return", "Re-render the visualization"),
            ("Save Plot", f"{ctrl} + Alt + S", "Export the plot to a file"),
            ("Pan Axes", "Middle Click + Drag", "Move around the plot canvas"),
            ("Select points", "Left Click + Drag", "Mark a selection of data"),
            ("Zoom In", "Scroll Up on the mouse wheel", "Zoom in to the canvas"),
            ("Zoom Out", "Scroll Down on the mouse wheel", "Zoom out on the canvas"),
            ("Open Python Editor", f"{ctrl} + Alt + E", "Open the code editor for custom scripts")
        ]

    def _populate_shortcuts(self) -> None:
        """Fill the table with shortcut mappings"""
        data = self._get_shortcut_data()
        self.table.setRowCount(len(data))

        for row, (name, key, description) in enumerate(data):
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(description)

            font = name_item.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            name_item.setFont(font)

            self.table.setItem(row, 0, name_item)

            key_item = QTableWidgetItem(key)
            self.table.setItem(row, 1, key_item)

    def _filter_shortcuts(self, query: str) -> None:
        """
        Filter table rows based on the search input
        :param query: The raw string text from the search bar
        """
        query_lower = query.lower()

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            key_item = self.table.item(row, 1)

            if not name_item or not key_item:
                continue

            name_match = query_lower in name_item.text().lower()
            key_match = query_lower in key_item.text().lower()
            desc_match = query_lower in name_item.toolTip().lower()

            self.table.setRowHidden(
                row, not (name_match or key_match or desc_match)
            )
