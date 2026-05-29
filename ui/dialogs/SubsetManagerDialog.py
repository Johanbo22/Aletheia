from ui.dialogs import CreateSubsetDialog, SubsetDataViewer, ProgressDialog
from core.data_handler import DataHandler
from core.subset_manager import SubsetManager
from ui.workers import AutoCreateSubsetsWorker

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QThreadPool
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox, QSplitter, QTextEdit, QVBoxLayout, QWidget, QMenu, QApplication, QFileDialog, QFormLayout, QFrame, QDialogButtonBox, QLineEdit, QGroupBox, QPushButton

from typing import Optional, Any

class SubsetDialogConstants:
    Title: str = "Data Subsets Tool"
    ModalWidth: int = 1115
    ModalHeight: int = 600
    MinModalWidth: int = 800
    MinModalHeight: int = 500
    PlaceholderText: str = "(No subsets created yet)"
    
    DescriptionMaxHeight: int = 60
    FiltersMaxHeight: int = 150
    ButtonSpacing: int = 10
    

class SubsetManagerDialog(QDialog):
    """Dialog for handling data susbets"""
    plot_subset_requested = pyqtSignal(str)

    def __init__(self, subset_manager: SubsetManager, data_handler: DataHandler, parent=None):
        super().__init__(parent)
        self.subset_manager = subset_manager
        self.data_handler = data_handler
        self.setWindowTitle(SubsetDialogConstants.Title)
        self.setModal(True)
        self.resize(SubsetDialogConstants.ModalWidth, SubsetDialogConstants.ModalHeight)
        self.setMinimumSize(SubsetDialogConstants.MinModalWidth, SubsetDialogConstants.MinModalHeight)

        self.init_ui()
        print(f"DEBUG: SubsetManager has {len(self.subset_manager.list_subsets())} subsets")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.data_handler.df is not None:
                print("DEBUG: Applying subsets to calculate row counts")
                self.apply_all_subsets()
            else:
                print("DEBUG: No data to apply subsets")
            print("DEBUG: Refreshing the subset list")
            self.refresh_subset_list()
        finally:
            QApplication.restoreOverrideCursor()

        print(f"DEBUG: QListWidget has {self.subset_list.count()} items")

    def apply_all_subsets(self):
        """Apply all subsets to calculate row counts"""
        print("DEBUG apply_all_subsets: Starting")

        if self.data_handler.df is None:
            print("WARNING apply_all_subsets: No data available")
            return

        if not hasattr(self, 'subset_manager'):
            print("ERROR apply_all_subsets: No subset_manager")
            return

        try:
            subset_names = self.subset_manager.list_subsets()
            print(f"DEBUG apply_all_subsets: Processing {len(subset_names)} subsets")

            for name in subset_names:
                try:
                    print(f"DEBUG apply_all_subsets: Applying subset '{name}'")
                    result_df = self.subset_manager.apply_subset(self.data_handler.df, name)
                    print(f"DEBUG apply_all_subsets: Subset '{name}' has {len(result_df)} rows")
                except Exception as ApplySubsetError:
                    print(f"WARNING apply_all_subsets: Could not apply subset {name}: {str(ApplySubsetError)}")
                    continue

        except Exception as ApplySubsetError:
            print(f"ERROR apply_all_subsets: {str(ApplySubsetError)}")
            import traceback
            traceback.print_exc()

    def init_ui(self):
        """Init ui for the dialog"""
        layout = QVBoxLayout()

        #title
        title = QLabel(SubsetDialogConstants.Title)
        title.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        #info
        info = QLabel(
            "Create named subsets (filtered views) of your data to create unique ways to analysing and visualize your data.\n"
            "Subsets do not modify your original data"
        )
        info.setWordWrap(True)
        info.setProperty("styleClass", "info_text")
        layout.addWidget(info)

        #main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("subset_manager_splitter")
        splitter.setHandleWidth(4)

        #left subset list
        left_widget = QWidget()
        left_widget.setMinimumWidth(250)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        
        self.list_group = QGroupBox("Existing Subsets", parent=self)
        list_group_layout = QVBoxLayout()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search subsets...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setToolTip("Search existing subsets (Ctrl+F)")
        self.search_bar.textChanged.connect(self.filter_subset_list)
        list_group_layout.addWidget(self.search_bar)
        
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.search_bar.setFocus)
        
        self.clear_search_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.search_bar)
        self.clear_search_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.clear_search_shortcut.activated.connect(self._clear_search_and_focus_list)

        self.subset_list = QListWidget()
        self.subset_list.setAlternatingRowColors(True)
        self.subset_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.subset_list.customContextMenuRequested.connect(self.show_context_menu)
        self.subset_list.itemClicked.connect(self.on_subset_selected)
        self.subset_list.itemDoubleClicked.connect(self.view_subset_data)
        list_group_layout.addWidget(self.subset_list)
        
        self.del_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.subset_list)
        self.del_shortcut.activated.connect(self.delete_subset)
        self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self.subset_list)
        self.backspace_shortcut.activated.connect(self.delete_subset)
        self.view_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.subset_list)
        self.view_shortcut.activated.connect(self.view_subset_data)

        print("DEBUG init_ui: Created subset_list QListWidget")

        # buttons for the list
        list_buttons = QHBoxLayout()
        
        has_data = self.data_handler.df is not None

        self.new_btn = QPushButton("New Subset", parent=self)
        self.new_btn.clicked.connect(self.create_new_subset)
        self.new_btn.setEnabled(has_data)
        if not has_data:
            self.new_btn.setToolTip("Please load data to create subsets")
        list_buttons.addWidget(self.new_btn)

        self.auto_create_btn = QPushButton("Auto create subsets by column", parent=self)
        self.auto_create_btn.clicked.connect(self.auto_create_subsets)
        self.auto_create_btn.setEnabled(has_data)
        if not has_data:
            self.auto_create_btn.setToolTip("Please load data to create subsets.")
        list_buttons.addWidget(self.auto_create_btn)

        list_group_layout.addLayout(list_buttons)
        self.list_group.setLayout(list_group_layout)
        left_layout.addWidget(self.list_group)

        splitter.addWidget(left_widget)

        #right subset detials
        right_widget = QWidget()
        right_widget.setMinimumWidth(400)
        right_layout = QVBoxLayout(right_widget)

        self.details_group = QGroupBox("Subset Details", parent=self)
        details_layout = QVBoxLayout()
        
        #name
        self.name_label = QLabel(SubsetDialogConstants.PlaceholderText)
        self.name_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.name_label.setObjectName("subset_name_label")
        self.name_label.setWordWrap(True)
        details_layout.addWidget(self.name_label)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setObjectName("subset_details_separator")
        details_layout.addWidget(separator)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        form_layout.setSpacing(10)
        
        self.rows_label = QLabel("-")
        form_layout.addRow("Rows:", self.rows_label)
        
        self.created_label = QLabel("-")
        form_layout.addRow("Created:", self.created_label)

        #description
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(SubsetDialogConstants.DescriptionMaxHeight)
        self.description_text.setProperty("styleClass", "subset_details_text")
        form_layout.addRow("Description:", self.description_text)

        #filters
        self.filters_text = QTextEdit()
        self.filters_text.setReadOnly(True)
        self.filters_text.setMaximumHeight(SubsetDialogConstants.FiltersMaxHeight)
        self.filters_text.setProperty("styleClass", "subset_details_text")
        form_layout.addRow("Filters:", self.filters_text)
        
        details_layout.addLayout(form_layout)
        details_layout.addSpacing(10)

        # Action buttons
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(SubsetDialogConstants.ButtonSpacing)

        data_actions_layout = QHBoxLayout()
        
        self.view_btn = QPushButton("View Data", parent=self)
        self.view_btn.clicked.connect(self.view_subset_data)
        self.view_btn.setToolTip("Open a new window to inspect the filtered dataset.")
        self.view_btn.setEnabled(False)
        data_actions_layout.addWidget(self.view_btn)

        self.plot_btn = QPushButton("Plot Subset", parent=self)
        self.plot_btn.clicked.connect(self.plot_subset)
        self.plot_btn.setToolTip("Switch to the Plot tab to visualize this specific subset.")
        self.plot_btn.setEnabled(False)
        data_actions_layout.addWidget(self.plot_btn)
        
        self.export_button = QPushButton("Export Subset", parent=self)
        self.export_button.clicked.connect(self.export_subset)
        self.export_button.setToolTip("Export the subset to a CSV file")
        self.export_button.setEnabled(False)
        data_actions_layout.addWidget(self.export_button)
        
        data_actions_layout.addStretch()
        action_buttons_layout.addLayout(data_actions_layout)
        
        management_actions_layout = QHBoxLayout()

        self.edit_btn = QPushButton("Edit", parent=self)
        self.edit_btn.clicked.connect(self.edit_subset)
        self.edit_btn.setToolTip("Modify the filter conditions or description.")
        self.edit_btn.setEnabled(False)
        management_actions_layout.addWidget(self.edit_btn)
        
        self.duplicate_btn = QPushButton("Duplicate", parent=self)
        self.duplicate_btn.clicked.connect(self.duplicate_subset)
        self.duplicate_btn.setToolTip("Create an exact copy of this subset's configuration")
        self.duplicate_btn.setEnabled(False)
        management_actions_layout.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("Delete", parent=self)
        self.delete_btn.setObjectName("DestructiveButton")
        self.delete_btn.clicked.connect(self.delete_subset)
        self.delete_btn.setToolTip("Permanently delete this subset configuration.")
        self.delete_btn.setEnabled(False)
        management_actions_layout.addWidget(self.delete_btn)

        management_actions_layout.addStretch()
        action_buttons_layout.addLayout(management_actions_layout)
        details_layout.addLayout(action_buttons_layout)

        self.details_group.setLayout(details_layout)
        right_layout.addWidget(self.details_group)

        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 600])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # bottom buttons [lmao 
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)
        self.setLayout(layout)
        
        print("DEBUG init_ui: UI initialization complete")
    
    def _clear_search_and_focus_list(self) -> None:
        self.search_bar.clear()
        self.subset_list.setFocus()

    def refresh_subset_list(self):
        """Refreshes the list of subsets"""
        print("DEBUG: resfresh_subset_list: Starting")
        print(f"DEBUG: refresh_subset_list: subset_list widget exists: {hasattr(self, "subset_list")}")

        if not hasattr(self, "subset_list"):
            print("ERROR: subset_list_widget not found")
            return

        self.subset_list.clear()
        self.subset_list.setSortingEnabled(False)
        print("DEBUG: refresh_subset_list: Cleared the list widget")

        subset_names = self.subset_manager.list_subsets()
        print(f"DEBUG refresh_subset_list: Found {len(subset_names)} subsets: {subset_names}")

        if not subset_names:
            placeholder = QListWidgetItem(SubsetDialogConstants.PlaceholderText)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.subset_list.addItem(placeholder)
            print("DEBUG: refresh_subset_list: Added placeholder for empty list")
            return

        for name in subset_names:
            try:
                subset = self.subset_manager.get_subset(name)
                if not subset:
                    print(f"WARNING: Subset '{name}' returned None from get_subset()")
                    continue

                row_text = f"{subset.row_count} rows" if subset.row_count > 0 else "? rows"
                item_text = f"{name} ({row_text})"
                print(f"DEBUG: refresh_subset_list: Adding item: {item_text}")

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, name)
                
                desc = subset.description if subset.description else "No description"
                item.setToolTip(f"<b>Description:</b> {desc}<br><b>Logic:</b> {subset.logic}")
                self.subset_list.addItem(item)
                print(f"DEBUG refresh_subset_list: Addded: {name}")

            except Exception as RefreshSubsetToListError:
                print(f"ERROR adding subset {name} to list: {str(RefreshSubsetToListError)}")
                import traceback
                traceback.print_exc()
                continue

        self.subset_list.setSortingEnabled(True)
        final_count = self.subset_list.count()
        print(f"DEBUG refresh_subset_list: Final item count: {final_count}")
    
    def show_context_menu(self, position: QPoint) -> None:
        """Displays a context menu for the selected subset item."""
        item = self.subset_list.itemAt(position)
        
        if not item or item.flags() & Qt.ItemFlag.NoItemFlags:
            return
        
        # Ensure the item is selected so the details panel stays synced
        self.subset_list.setCurrentItem(item)
        self.on_subset_selected(item)
        
        menu = QMenu(self)
        view_action = menu.addAction("View Data")
        plot_action = menu.addAction("Plot Subset")
        export_action = menu.addAction("Export Subset")
        menu.addSeparator()
        duplicate_action = menu.addAction("Duplicate")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(self.subset_list.mapToGlobal(position))
        
        if action == view_action:
            self.view_subset_data()
        elif action == plot_action:
            self.plot_subset()
        elif action == export_action:
            self.export_subset()
        elif action == duplicate_action:
            self.duplicate_subset()
        elif action == edit_action:
            self.edit_subset()
        elif action == delete_action:
            self.delete_subset()
    
    def filter_subset_list(self, search_text: str) -> None:
        """Filters the subset list visually based on the search query."""
        has_visible_selection = False
        
        for index in range(self.subset_list.count()):
            item = self.subset_list.item(index)
            # Skip the placeholder item 
            if item.flags() & Qt.ItemFlag.NoItemFlags:
                continue
            
            subset_name = item.data(Qt.ItemDataRole.UserRole)
            if subset_name:
                # Show item if search is in the subsetname, case-insensitive
                is_match = search_text.lower() in subset_name.lower()
                item.setHidden(not is_match)
                
                if item.isSelected() and is_match:
                    has_visible_selection = True
                    
        if not has_visible_selection and self.subset_list.currentItem():
            self.subset_list.clearSelection()
            self._clear_details_panel()

    def on_subset_selected(self, item):
        """Subset selection"""
        # Check if item is the placeholder
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        subset = self.subset_manager.get_subset(name)

        if not subset:
            QMessageBox.warning(self, "Error", f"Subset '{name}' not found")
            return
        
        # Calculate percentage on original dataframe
        total_rows = len(self.data_handler.df) if self.data_handler.df is not None else 0
        if subset.row_count > 0 and total_rows > 0:
            pct = (subset.row_count / total_rows) * 100
            row_display = f"{subset.row_count} ({pct:.1f}% of original data)"
        else:
            row_display = str(subset.row_count) if subset.row_count > 0 else "?"

        # Update UI with subset information
        self.name_label.setText(name)
        self.description_text.setText(subset.description or "No Description")
        self.rows_label.setText(row_display)
        self.created_label.setText(subset.created_at.strftime("%Y-%m-%d %H:%M"))

        html_text = f"<p><b>Logic:</b> <span style='color: #2b5797;'>{subset.logic}</span></p>"
        if subset.filters:
            html_text += "<ul style='margin-top: 0px; padding-left: 20px;'>"
            for f in subset.filters:
                html_text += f"<li><b>{f['column']}</b> <i>{f['condition']}</i> '{f['value']}'</li>"
            html_text += "</ul>"
        else:
            html_text += "<p><i>No filters applied.</i></p>"
        
        self.filters_text.setHtml(html_text)

        # Enable buttons
        self.view_btn.setEnabled(True)
        self.plot_btn.setEnabled(True)
        self.duplicate_btn.setEnabled(True)
        self.export_button.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def create_new_subset(self):
        """Create a new subset"""
        if self.data_handler.df is None:
            QMessageBox.warning(self, "No Data", "Please load data first")
            return

        dialog = CreateSubsetDialog(
            self.data_handler,
            self
        )

        if dialog.exec():
            config = dialog.get_config()
            try:
                self.subset_manager.create_subset(
                    name=config["name"],
                    description=config["description"],
                    filters=config["filters"],
                    logic=config["logic"]
                )

                #apply 
                self.subset_manager.apply_subset(self.data_handler.df, config["name"])

                self.refresh_subset_list()
                items = self.subset_list.findItems(config["name"], Qt.MatchFlag.MatchExactly)
                if items:
                    self.subset_list.setCurrentItem(items[0])
                    self.on_subset_selected(items[0])

                QMessageBox.information(self, "Success", f"Subset '{config['name']}' created")
            except ValueError as CreateNewSubsetError:
                QMessageBox.warning(self, "Error", str(CreateNewSubsetError))

    def auto_create_subsets(self):
        """Auto create subsets based on unique values in a column"""
        if self.data_handler.df is None:
            QMessageBox.warning(self, "No Data", "Please load data first")
            return

        column, ok = QInputDialog.getItem(
            self,
            "Auto-Create Subsets",
            "Select column to split by:",
            self.data_handler.df.columns.tolist(),
            0,
            False
        )

        if ok and column:
            unique_count = self.data_handler.df[column].nunique()

            reply = QMessageBox.question(
                self,
                "Confirm",
                f"This will create {unique_count} subsets (one for each unique value in '{column}').\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.progress_dialog = ProgressDialog(
                    title="Auto-Creating Subsets",
                    message=f"Creating subsets from '{column}'...",
                    parent=self
                )
                self.progress_dialog.setModal(True)
                self.progress_dialog.show()

                worker = AutoCreateSubsetsWorker(self.subset_manager, self.data_handler.df, column)
                worker.signals.progress.connect(self.progress_dialog.update_progress)
                worker.signals.finished.connect(lambda created: self._on_auto_create_finished(created, column))
                worker.signals.error.connect(self._on_auto_create_error)

                QThreadPool.globalInstance().start(worker)
    
    def _on_auto_create_finished(self, created: list, column: str) -> None:
        """Handles completion of auto-creating subsets in the background."""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

        self.refresh_subset_list()
        QMessageBox.information(
            self,
            "Success",
            f"Created {len(created)} subsets from column '{column}'"
        )

    def _on_auto_create_error(self, error: Exception) -> None:
        """Handles errors from the auto-create subsets worker."""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

        QMessageBox.critical(self, "Error", str(error))
    
    def _clear_details_panel(self) -> None:
        """Resets the detail panel UI to its default, unselected state."""
        self.name_label.setText(SubsetDialogConstants.PlaceholderText)
        self.description_text.clear()
        self.rows_label.setText("-")
        self.created_label.setText("-")
        self.filters_text.clear()
        
        self.view_btn.setEnabled(False)
        self.plot_btn.setEnabled(False)
        self.duplicate_btn.setEnabled(False)
        self.export_button.setEnabled(False)
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def view_subset_data(self):
        """View the filtered data for a selected subset"""
        item = self.subset_list.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        try:
            subset_df = self.subset_manager.apply_subset(self.data_handler.df, name)

            #show in new dialog
            viewer = SubsetDataViewer(subset_df, name, self)
            viewer.exec()
        except Exception as ViewSubsetDataError:
            QMessageBox.critical(self, "Error", str(ViewSubsetDataError))

    def plot_subset(self):
        """Switch to plot tab with subset data active"""
        item = self.subset_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a subset you wish to visualize")
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            return

        self.plot_subset_requested.emit(name)
        self.accept()

    def edit_subset(self):
        """Edit the selected subset"""
        item = self.subset_list.currentItem()
        if not item:
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        subset = self.subset_manager.get_subset(name)

        dialog = CreateSubsetDialog(
            self.data_handler,
            self,
            existing_subset=subset
        )

        if dialog.exec():
            config = dialog.get_config()
            try:
                self.subset_manager.update_subset(
                    name=name,
                    description=config["description"],
                    filters=config["filters"],
                    logic=config["logic"]
                )

                # apply agian
                self.subset_manager.apply_subset(self.data_handler.df, name, use_cache=False)

                self.refresh_subset_list()
                self.on_subset_selected(item)
                QMessageBox.information(self, "Success", f"Subset '{name}' updated")
            except Exception as EditSubsetError:
                QMessageBox.warning(self, "Error", str(EditSubsetError))

    def delete_subset(self):
        """Delete the selected subset"""
        item = self.subset_list.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        current_row = self.subset_list.currentRow()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete subset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.subset_manager.delete_subset(name)
            self.refresh_subset_list()

            if self.subset_list.count() > 0:
                first_item = self.subset_list.item(0)
                if not (first_item.flags() & Qt.ItemFlag.NoItemFlags):
                    next_row = min(current_row, self.subset_list.count() - 1)
                    next_item = self.subset_list.item(next_row)
                    self.subset_list.setCurrentItem(next_item)
                    self.on_subset_selected(next_item)
                else:
                    self._clear_details_panel()
            else:
                self._clear_details_panel()
    
    def duplicate_subset(self) -> None:
        """Creates an exact copy of the selected subset to allow rapid iteration."""
        item = self.subset_list.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return
        
        name = item.data(Qt.ItemDataRole.UserRole)
        subset = self.subset_manager.get_subset(name)
        
        if not subset:
            return
        
        # Generate a unique name for the copy
        new_name = f"{name} (Copy)"
        counter = 1
        while new_name in self.subset_manager.list_subsets():
            new_name = f"{name} (Copy {counter})"
            counter += 1
        
        try:
            self.subset_manager.create_subset(name=new_name, description=subset.description, filters=subset.filters, logic=subset.logic)
            self.subset_manager.apply_subset(self.data_handler.df, new_name)
            self.refresh_subset_list()
            
            items = self.subset_list.findItems(new_name, Qt.MatchFlag.MatchContains)
            if items:
                self.subset_list.setCurrentItem(items[0])
                self.on_subset_selected(items[0])
            QMessageBox.information(self, "Success", f"Subset duplicated as '{new_name}'.")
        except Exception as DuplicateError:
            QMessageBox.warning(self, "Error", f"Could not duplicate subset: {str(DuplicateError)}")
    
    def export_subset(self) -> None:
        """Exports the subset data directly to a CSV file."""
        item = self.subset_list.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return
        
        name = item.data(Qt.ItemDataRole.UserRole)
        
        # Open file save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Subset Data",
            f"{name}_subset.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                subset_df = self.subset_manager.apply_subset(self.data_handler.df, name)
                subset_df.to_csv(file_path, index=False)
                QApplication.restoreOverrideCursor()
                
                QMessageBox.information(self, "Export Successful", f"Subset successfully exported to:\n{file_path}")
            except Exception as ExportError:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Export Failed", f"An error occurred during export:\n{str(ExportError)}")