# ui/data_tab.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QTableView, QHeaderView, QGraphicsOpacityEffect, QMenu, QStackedWidget, QApplication, QTabWidget, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize, QTimer, QModelIndex
from PyQt6.QtGui import QIcon, QFont, QAction, QPalette, QColor, QShortcut, QKeySequence

from core.data_handler import DataHandler
from core.resource_loader import get_resource_path
from ui.status_bar import StatusBar
from ui.dialogs import TableCustomizationDialog
from core.subset_manager import SubsetManager
from pathlib import Path

from ui.data_table_model import DataTableModel
from ui.theme import ThemeColors
from ui.icons import IconBuilder, IconType
from ui.components.data_operations_panel import DataOperationsPanel
from ui.components.statistics_generator import StatisticsGenerator
from ui.components.data_table_delegate import DataTableDelegate
from ui.components.data_search_bar import DataSearchBar
from ui.components.data_view_toolbar import DataViewToolbar
from ui.LandingPage import LandingPage
from ui.icons import IconBuilder, IconType

from ui.animations import (
    EditModeToggleAnimation
)
from ui.controllers.data_tab_controller import DataTabController
from ui.workers import SearchWorker


class DataTab(QWidget):
    """Tab for viewing and manipulating data"""

    request_open_project = pyqtSignal()
    request_recent_project = pyqtSignal(str)
    request_import_file = pyqtSignal()
    request_import_sheets = pyqtSignal()
    request_import_db = pyqtSignal()
    request_open_settings = pyqtSignal()
    request_quit = pyqtSignal()
    request_python_console = pyqtSignal()
    data_modified = pyqtSignal()

    def __init__(
        self,
        data_handler: DataHandler,
        status_bar: StatusBar,
        subset_manager: SubsetManager,
    ):
        super().__init__()

        self.data_handler = data_handler
        self.status_bar = status_bar
        self.subset_manager = subset_manager
        self.controller = DataTabController(data_handler=self.data_handler, status_bar=self.status_bar, view=self, subset_manager=self.subset_manager)
        self.stats_generator = StatisticsGenerator()
        self.plot_tab = None
        self.data_table = None
        self.stats_text = None
        self.data_tabs = None
        self.subset_view_label = None
        self.aggregation_view_label = None
        self.is_editing = False
        
        self.current_precision = 2
        self.current_formatting_rules = []
        self.current_render_bools = True

        self.current_nan_display = "NaN"
        self.current_thousands_sep = False
        self.current_scientific_notation = False
        self.current_grid_style = "Solid Line"
        self.current_grid_color = "#D3D3D3"

        self.init_ui()

    def set_plot_tab(self, plot_tab):
        """Sets a reference to the PlotTab"""
        self.plot_tab = plot_tab

    def init_ui(self):
        """Initialize the data tab UI"""
        main_layout = QHBoxLayout(self)

        # Left side: Data table and operations stacked with landing page
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.left_stack = QStackedWidget()
        left_layout.addWidget(self.left_stack)

        # Landing page
        self.landing_page = LandingPage()
        self.landing_page.open_project_clicked.connect(self.request_open_project.emit)
        self.landing_page.recent_project_clicked.connect(self.request_recent_project.emit)
        self.landing_page.import_file_clicked.connect(self.request_import_file.emit)
        self.landing_page.import_sheets_clicked.connect(self.request_import_sheets.emit)
        self.landing_page.import_db_clicked.connect(self.request_import_db.emit)
        self.landing_page.new_dataset_clicked.connect(self.controller.create_new_dataset)
        self.landing_page.settings_clicked.connect(self.request_open_settings.emit)
        self.landing_page.quit_clicked.connect(self.request_quit.emit)
        self.left_stack.addWidget(self.landing_page)

        # Data view container
        self.data_view_widget = QWidget()
        data_view_layout = QVBoxLayout(self.data_view_widget)
        data_view_layout.setContentsMargins(0, 0, 0, 0)
        data_view_layout.setSpacing(6)
        self.left_stack.addWidget(self.data_view_widget)

        # Data toolbar
        self.toolbar = DataViewToolbar(parent=self)
        self.toolbar.create_dataset_requested.connect(self.controller.create_new_dataset)
        self.toolbar.refresh_data_requested.connect(self.controller.refresh_google_sheets)
        self.toolbar.python_console_requested.connect(self.request_python_console.emit)
        self.toolbar.edit_mode_toggled.connect(self.toggle_edit_mode)
        data_view_layout.addWidget(self.toolbar)

        # Search bar
        self.search_bar = DataSearchBar(data_handler=self.data_handler, parent=self)
        self.search_bar.match_found.connect(self.highlight_cell)
        self.search_bar.clear_selection_requested.connect(lambda: self.data_table.clearSelection() if self.data_handler else None)
        
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.open_search_bar)

        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self.search_bar)
        self.esc_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.esc_shortcut.activated.connect(self.search_bar.close_search)
        data_view_layout.addWidget(self.search_bar)

        # Create tabs for data and statistics
        self.data_tabs = QTabWidget()

        # Data Table Tab
        self.data_table = QTableView()
        self.data_table.setObjectName("MainDataTable")
        self.data_table.horizontalHeader().setObjectName("MainDataHeader")
        self.data_table.verticalHeader().setObjectName("MainDataHeader")
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)

        self.table_delegate = DataTableDelegate(self.data_table)
        self.data_table.setItemDelegate(self.table_delegate)
        self.data_table.verticalHeader().setDefaultSectionSize(32)

        self.data_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.data_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.data_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        
        palette = self.data_table.palette()
        active_highlight = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight)
        active_text = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, active_highlight)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, active_text)
        self.data_table.setPalette(palette)

        # Data table context menu
        self.data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        self.data_table.horizontalHeader().sectionClicked.connect(self._on_horizontal_header_clicked)
        self.data_table.verticalHeader().sectionClicked.connect(self._on_vertical_header_clicked)
        
        self.copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.data_table)
        self.copy_shortcut.activated.connect(self.copy_selection)

        data_table_icon = IconBuilder.build(IconType.DataExplorerIcon)
        self.data_tabs.addTab(self.data_table, data_table_icon, "Data Table")

        # Statistics Tab
        self.stats_text = QWebEngineView()
        self.stats_text.page().setBackgroundColor(QColor(Qt.GlobalColor.transparent))

        self.stats_opacity_effect = QGraphicsOpacityEffect(self.stats_text)
        self.stats_text.setGraphicsEffect(self.stats_opacity_effect)
        stats_icon = IconBuilder.build(IconType.ExploreStatisticsIcon)
        self.data_tabs.addTab(self.stats_text, stats_icon, "Statistics")
        
        self.test_results_text = QWebEngineView()
        self.test_results_text.page().setBackgroundColor(QColor(Qt.GlobalColor.transparent))
        
        self.set_test_results_greeting()
        test_result_icon = IconBuilder.build(IconType.Calculator)
        self.data_tabs.addTab(self.test_results_text, test_result_icon, "Test Results")

        data_view_layout.addWidget(self.data_tabs, 1)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.operations_panel = DataOperationsPanel(parent=self, controller=self.controller)

        right_layout.addWidget(self.operations_panel)
        self.right_widget = right_widget

        # Create splitter
        from PyQt6.QtWidgets import QSplitter

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.refresh_data_view()

    def toggle_edit_mode(self, is_editing: bool) -> None:
        """
        Toggles the edit mode in the data table based on toolbar state
        """
        self.is_editing = is_editing

        if self.is_editing:
            self.data_table.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed)
            self.status_bar.log("Edit Mode Enabled. You are now able to edit cells in the data table", "INFO")

            EditModeToggleAnimation(parent=self, is_on=True).start(target_widget=self)
        else:
            self.data_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
            self.status_bar.log("Edit Mode Disabled", "INFO")
            EditModeToggleAnimation(parent=self, is_on=False).start(target_widget=self)

        # Update the flags
        if self.data_table.model() is not None and isinstance(self.data_table.model(), DataTableModel):
            self.data_table.model().set_editable(self.is_editing)
        else:
            self.refresh_data_view()

    def open_search_bar(self) -> None:
        """Show the inline search bar and focus input"""
        if self.data_handler.df is None:
            return
        self.search_bar.open_search()

    def highlight_cell(self, row_index: int, column_index: int):
        """Scrolls to and highlights the specified index cell in the data table"""
        if self.data_table.model() is None:
            return

        index = self.data_table.model().index(row_index, column_index)
        if index.isValid():
            from PyQt6.QtCore import QItemSelectionModel
            self.data_table.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
            self.data_table.setCurrentIndex(index)
            self.data_table.scrollTo(index, QTableView.ScrollHint.PositionAtCenter)
            self.data_table.setFocus()
    
    def _on_horizontal_header_clicked(self, logical_index: int) -> None:
        """Handles horizontal header clicks for inserting columns"""
        model = self.data_table.model()
        if not isinstance(model, DataTableModel) or not model.editable or model._data is None:
            return
        if logical_index == model._data.shape[1]:
            model.insert_empty_column()
    
    def _on_vertical_header_clicked(self, logical_index: int) -> None:
        """Handles vertical header clicks to insert rows"""
        model = self.data_table.model()
        if not isinstance(model, DataTableModel) or not model.editable or model._data is None:
            return
        if logical_index == model._data.shape[0]:
            model.insert_empty_row()

    def refresh_data_view(self, reload_model: bool = True):
        """Refresh the data table and statistics"""
        if self.data_handler.df is None:
            self._handle_empty_data_view()
            return
        
        if hasattr(self, "left_stack"):
            self.left_stack.setCurrentIndex(1)
        if hasattr(self, "right_widget"):
            self.right_widget.setVisible(True)
        
        # UI updaters
        self._update_data_model(reload_model)
        self._update_edit_triggers()
        self._update_column_selectors()
        self.update_statistics()
        self._update_data_source_status()
        self._update_subsets_status()
        self._update_history_list()
        self.data_modified.emit()
    
    def _handle_empty_data_view(self) -> None:
        """Clears the UI when no data is loaded"""
        if hasattr(self, "left_stack"):
            self.left_stack.setCurrentIndex(0)

        if hasattr(self, "right_widget"):
            self.right_widget.setVisible(False)

        if hasattr(self, "data_table") and self.data_table is not None:
            self.data_table.setModel(None)

        if hasattr(self, "stats_text") and self.stats_text is not None:
            self.stats_text.setHtml("")

        if hasattr(self, "toolbar"):
            self.toolbar.set_refresh_visible(False)

        self.status_bar.set_data_source("")
        self.status_bar.set_view_context("", "normal")
    
    def _update_data_model(self, reload_model: bool) -> None:
        """Updates the table model and restores sorting states"""
        if not reload_model:
            return
        
        df = self.data_handler.df
        if hasattr(self, "model") and isinstance(self.model, DataTableModel):
            self.model.update_data()
            self.data_table.setSortingEnabled(False)
        else:
            self.model = DataTableModel(self.data_handler, editable=self.is_editing, float_precision=self.current_precision, conditional_rules=self.current_formatting_rules)
            self.model.set_bool_render_style(getattr(self, "current_render_bools", True))

            if hasattr(self.model, "set_nan_display"):
                self.model.set_nan_display(getattr(self, "current_nan_display", "NaN"))
            if hasattr(self.model, "set_thousands_separator"):
                self.model.set_thousands_separator(getattr(self, "current_thousands_sep", False))
            if hasattr(self.model, "set_scientific_notation"):
                self.model.set_scientific_notation(getattr(self, "current_scientific_notation", False))

            self.model.columnsInserted.connect(self._update_column_selectors)
            self.data_table.setSortingEnabled(False)
            self.data_table.setModel(self.model)
        
        header = self.data_table.horizontalHeader()
        header.blockSignals(True)
        
        if self.data_handler.sort_state:
            col_name, ascending = self.data_handler.sort_state
            try:
                col_index = list(df.columns).index(col_name)
                order = (Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder)
                header.setSortIndicator(col_index, order)
            except ValueError:
                header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        else:
            header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        
        header.blockSignals(False)
        self.data_table.setSortingEnabled(True)
    
    def _update_edit_triggers(self) -> None:
        """Sets the table edit triggers based on the editing state"""
        if self.is_editing:
            self.data_table.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed)
        else:
            self.data_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
            
    def _update_column_selectors(self) -> None:
        """Updates column selection boxes"""
        df = self.data_handler.df
        columns = list(df.columns)
        panel = self.operations_panel
        
        panel.filtering_tab.filter_column.clear()
        panel.filtering_tab.filter_column.addItems(columns)
        panel.columns_tab.column_list.clear()
        panel.columns_tab.column_list.addItems(columns)
        panel.datetime_tab.dt_source_combo.clear()
        panel.datetime_tab.dt_source_combo.addItems(columns)
        panel.datetime_tab.dt_start_combo.clear()
        panel.datetime_tab.dt_start_combo.addItems(columns)
        panel.datetime_tab.dt_end_combo.clear()
        panel.datetime_tab.dt_end_combo.addItems(columns)
        
        if hasattr(panel, "transform_tab") and hasattr(panel.transform_tab, "sort_column_combo"):
            current_sort = panel.transform_tab.sort_column_combo.currentText()
            panel.transform_tab.sort_column_combo.clear()
            panel.transform_tab.sort_column_combo.addItems(columns)
            if current_sort and current_sort in columns:
                panel.transform_tab.sort_column_combo.setCurrentText(current_sort)
            elif (self.data_handler.sort_state and self.data_handler.sort_state[0] in columns):
                panel.transform_tab.sort_column_combo.setCurrentText(self.data_handler.sort_state[0])
                
        if hasattr(panel, "subsets_tab") and hasattr(panel.subsets_tab, "subset_column_combo"):
            try:
                panel.subsets_tab.subset_column_combo.clear()
                panel.subsets_tab.subset_column_combo.addItems(columns)
            except Exception as Error:
                print(f"Warning: Could not update subset columns: {str(Error)}")
        
        if self.plot_tab:
            self.plot_tab.update_column_combo()
    
    def _update_data_source_status(self) -> None:
        """Updates the status bar and refreshes butotns based on datat source"""
        if self.data_handler.has_google_sheets_import():
            self.toolbar.set_refresh_visible(True)
            display_name = self.data_handler.last_gsheet_name
            if not display_name:
                display_name = f"GID: {self.data_handler.last_gsheet_gid}"
            self.status_bar.set_data_source(f"Google Sheets: {display_name}")
        elif hasattr(self.data_handler, "file_path") and self.data_handler.file_path:
            try:
                file_name = Path(self.data_handler.file_path).name
            except Exception:
                file_name = str(self.data_handler.file_path)

            self.status_bar.set_data_source(f"Local File: {file_name}")
            self.toolbar.set_refresh_visible(False)
        else:
            self.status_bar.set_data_source("New")
            self.toolbar.set_refresh_visible(False)
    
    def _update_subsets_status(self) -> None:
        """Refreshes subset info and updates status bar"""
        try:
            if hasattr(self, "subset_manager"):
                self.subset_manager.clear_cache()
            if hasattr(self, "active_subsets_list"):
                self.controller.refresh_active_subsets()
        except Exception as Error:
            print(f"Warning: Could not refresh subsets: {Error}")
        
        inserted_name = getattr(self.data_handler, "inserted_subset_name", None)
        agg_name = getattr(self.data_handler, "viewing_aggregation_name", None)
        
        if agg_name:
            self.status_bar.set_view_context(f"Viewing Aggregation: {agg_name}")
        elif inserted_name:
            self.status_bar.set_view_context(f"Viewing Subset: {inserted_name}")
        else:
            self.status_bar.set_view_context("", "normal")

    def _update_history_list(self) -> None:
        """Updates the history list and pipeline graph for the branching tree system."""
        panel = self.operations_panel
        if not hasattr(panel, "history_tab") or not hasattr(panel.history_tab, "history_list"):
            return

        panel.history_tab.history_list.clear()

        history_information = self.data_handler.get_history_info()
        nodes_dict = history_information.get("nodes", {})
        current_node_id = history_information.get("current_node_id")
        root_id = history_information.get("root_id")

        if not nodes_dict or not current_node_id or not root_id:
            return

        for node in nodes_dict.values():
            if node.diff_record and "type" not in node.diff_record.metadata:
                node.diff_record.metadata["type"] = node.diff_record.operation_type.value

        path_to_current = []
        curr = current_node_id
        while curr:
            path_to_current.append(curr)
            curr = nodes_dict[curr].parent_id if curr in nodes_dict else None
        path_to_current.reverse()

        item_height = 32

        def style_item(item: QListWidgetItem, is_active: bool, text: str) -> None:
            item.setSizeHint(QSize(0, item_height))
            font = item.font()
            font.setPointSize(9)

            if is_active:
                item.setText(f"{text}  ← Active")
                font.setWeight(QFont.Weight.Bold)
                item.setFont(font)
                try:
                    active_color = QColor(ThemeColors.MainColor)
                    bg_color = QColor(ThemeColors.MainColor)
                    bg_color.setAlpha(25)
                except Exception:
                    active_color = QColor("#2563eb")
                    bg_color = QColor("#dbeafe")
                item.setForeground(active_color)
                item.setBackground(bg_color)
            else:
                item.setText(text)
                font.setWeight(QFont.Weight.Medium)
                item.setFont(font)
                item.setForeground(QColor("#334155"))

        initial_item = QListWidgetItem("0. Initial Data")
        initial_item.setData(Qt.ItemDataRole.UserRole, root_id)
        initial_item.setIcon(IconBuilder.build(IconType.DataExplorerIcon))
        initial_item.setToolTip("The original data state upon import or creation")
        style_item(initial_item, root_id == current_node_id, "0. Initial Data")
        panel.history_tab.history_list.addItem(initial_item)

        for i, node_id in enumerate(path_to_current):
            if node_id == root_id: continue

            node = nodes_dict[node_id]
            operation = node.diff_record.metadata
            operation_type = operation.get("type", "Unknown")
            operation_text = self._format_operation_text(operation)

            item = QListWidgetItem(f"{i}. {operation_text}")
            item.setData(Qt.ItemDataRole.UserRole, node_id)
            item.setIcon(self._get_icon_for_operation(operation_type))

            details = "".join(
                f"<li><b>{k}</b>: {v}</li>" for k, v in operation.items() if k != "type" and not k.endswith("_index"))
            item.setToolTip(
                f"<b>Operation Details:</b><br><ul style='margin-top: 4px; margin-bottom: 0px;'>{details}</ul>")

            style_item(item, node_id == current_node_id, f"{i}. {operation_text}")
            panel.history_tab.history_list.addItem(item)

        if current_node_id in nodes_dict:
            for child_id in nodes_dict[current_node_id].children_ids:
                child_node = nodes_dict[child_id]
                operation = child_node.diff_record.metadata
                operation_type = operation.get("type", "Unknown")
                operation_text = self._format_operation_text(operation)

                item = QListWidgetItem(f"↳ [Branch] {operation_text}")
                item.setData(Qt.ItemDataRole.UserRole, child_id)
                item.setIcon(self._get_icon_for_operation(operation_type))

                font = item.font()
                font.setItalic(True)
                font.setPointSize(9)
                item.setFont(font)
                item.setForeground(QColor("#94A3B8"))
                item.setSizeHint(QSize(0, item_height))

                panel.history_tab.history_list.addItem(item)

        for i in range(panel.history_tab.history_list.count()):
            if panel.history_tab.history_list.item(i).data(Qt.ItemDataRole.UserRole) == current_node_id:
                panel.history_tab.history_list.scrollToItem(panel.history_tab.history_list.item(i))
                break

        if hasattr(panel.history_tab, "pipeline_graph"):
            panel.history_tab.pipeline_graph.build_graph(nodes_dict, root_id, current_node_id,
                                                         self._format_operation_text)
    
    def _get_icon_for_operation(self, operation_type: str) -> QIcon:
        match operation_type:
            case "filter" | "filter_multiple":
                return IconBuilder.build(IconType.Filter)
            case "drop_column":
                return IconBuilder.build(IconType.DropColumn)
            case "rename_column":
                return IconBuilder.build(IconType.RenameColumn)
            case "change_data_type":
                return IconBuilder.build(IconType.ChangeDataType)
            case "fill_missing":
                return IconBuilder.build(IconType.FillMissingValues)
            case "drop_missing":
                return IconBuilder.build(IconType.DropMissingValues)
            case "drop_duplicates":
                return IconBuilder.build(IconType.RemoveDuplicates)
            case "aggregate" | "melt" | "pivot" | "merge" | "concatenate" | "bin_column" | "normalize":
                return IconBuilder.build(IconType.DataTransform)
            case "sort":
                return IconBuilder.build(IconType.Sort)
            case "computed_column":
                return IconBuilder.build(IconType.Calculator)
            case "text_manipulation" | "split_column" | "regex_replace":
                return IconBuilder.build(IconType.TextOperation)
            case "duplicate_column":
                return IconBuilder.build(IconType.DuplicateColumn)
            case "extract_date_component" | "calculate_date_difference":
                return IconBuilder.build(IconType.DatetimeTools)
            case "remove_rows" | "clip_outliers" | "flag_outliers":
                return IconBuilder.build(IconType.DataCleaning)
            case _:
                return IconBuilder.build(IconType.History)

    def switch_to_plot_tab(self):
        """Helper to swtich to the plot tab"""
        current_widget = self.parentWidget()
        found_tab_widget = False
        while current_widget:
            if isinstance(current_widget, QTabWidget):
                current_widget.setCurrentWidget(self.plot_tab)
                found_tab_widget = True
                break
            current_widget = current_widget.parentWidget()
        if not found_tab_widget:
            self.status_bar.log("Could not switch to plot tab: Tab Widget not found", "WARNING")

    def update_statistics(self) -> None:
        """Update statistics display"""
        if self.data_handler.df is None:
            return
        
        try:
            info = self.data_handler.get_data_info()
            df = self.data_handler.df
        except Exception as UpdateStatisticsError:
            self.stats_text.setHtml(
                f"<p style='color: red;'>Error loading data info: {str(UpdateStatisticsError)}</p>"
            )
            return
        
        # Generate HTML
        final_html = self.stats_generator.generate_html(df, info)
        self.stats_text.setHtml(final_html)
        
        self.stats_animation = QPropertyAnimation(self.stats_opacity_effect, b"opacity")
        self.stats_animation.setDuration(500)
        self.stats_animation.setStartValue(0.0)
        self.stats_animation.setEndValue(1.0)
        self.stats_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.stats_animation.start()

    def clear(self):
        """Clear the data tab"""
        self.data_table.setModel(None)
        self.stats_text.setHtml("")
        if hasattr(self, "test_results_text"):
            self.set_test_results_greeting()

        if hasattr(self, "toolbar"):
            self.toolbar.set_refresh_visible(False)
        self.status_bar.set_data_source("")
        self.status_bar.set_view_context("", "normal")

    def _format_operation_text(self, operation: dict) -> str:
        """Formatter for operation dict back to better text handling"""
        operation_type = operation.get("type", "Unknown")

        match operation_type:
            case "filter":
                return f"Filter: {operation.get('column')} {operation.get('condition')} '{operation.get('value')}'"
            case "filter_multiple":
                filters = operation.get("filters", [])
                return f"Advanced Filter ({len(filters)} conditions)"
            case "drop_column":
                cols = operation.get("columns", operation.get("column", ""))
                if isinstance(cols, list):
                    return f"Drop Columns: {', '.join(cols)}"
                return f"Drop Column: {cols}"
            case "rename_column":
                return f"Rename: {operation.get('old_name')} -> {operation.get('new_name')}"
            case "change_data_type":
                return f"Data type change: {operation.get('column')} -> {operation.get('new_type')}"
            case "fill_missing":
                col = operation.get("column", "All Columns")
                return f"Fill missing: {col} ({operation.get('method')})"
            case "drop_missing":
                return "Drop missing Values"
            case "drop_duplicates":
                return "Remove Duplicate Values"
            case "aggregate":
                group_by = operation.get("group_by", [])
                return f"Aggregate: Grouped by {len(group_by)} cols"
            case "melt":
                return "Melt/Unpivot Data"
            case "pivot":
                index_cols = operation.get("index", [])
                return f"Pivot Table (Index: {index_cols})"
            case "merge":
                return f"Merge Data ({operation.get('how', 'inner')})"
            case "concatenate":
                return "Append / Concatenate Data"
            case "sort":
                direction = "Asc" if operation.get("ascending") else "Desc"
                return f"Sort: {operation.get('column')} ({direction})"
            case "computed_column":
                return f"Compute: {operation.get('new_column')}"
            case "bin_column":
                return f"Bin: {operation.get('column')} -> {operation.get('new_column')}"
            case "text_manipulation":
                return f"Text Op: {operation.get('operation')} on {operation.get('column')}"
            case "split_column":
                return f"Split: {operation.get('column')}"
            case "regex_replace":
                return f"Regex Replace on {operation.get('column')}"
            case "remove_rows":
                rows = operation.get("rows", [])
                return f"Remove Rows ({len(rows)} rows)"
            case "clip_outliers":
                return f"Clip Outliers ({operation.get('method')})"
            case "duplicate_column":
                return f"Duplicate: {operation.get('column')} -> {operation.get('new_column')}"
            case "normalize":
                return f"Normalize ({operation.get('method')})"
            case "extract_date_component":
                return f"Extract: {operation.get('component')} from {operation.get('column')}"
            case "calculate_date_difference":
                return f"Date Diff: {operation.get('end_column')} - {operation.get('start_column')}"
            case "flag_outliers":
                return f"Flag Outliers: {operation.get('new_column_name')}"
            case _:
                return f"{operation_type.replace('_', ' ').title()}"

    def show_table_context_menu(self, position):
        """Shows the context menu for the data table"""
        if self.data_handler.df is None:
            return

        menu = QMenu()

        resize_cols_action = menu.addAction("Resize Columns to Contents")
        resize_rows_action = menu.addAction("Resize Rows to Contents")
        menu.addSeparator()

        grid_action = QAction("Show Grid", menu)
        grid_action.setCheckable(True)
        grid_action.setChecked(self.data_table.showGrid())
        grid_action.triggered.connect(
            lambda: self.data_table.setShowGrid(grid_action.isChecked())
        )
        menu.addAction(grid_action)

        alt_rows_action = QAction("Alternating Colors", menu)
        alt_rows_action.setCheckable(True)
        alt_rows_action.setChecked(self.data_table.alternatingRowColors())
        alt_rows_action.triggered.connect(
            lambda: self.data_table.setAlternatingRowColors(alt_rows_action.isChecked())
        )
        menu.addAction(alt_rows_action)

        menu.addSeparator()
        copy_action = menu.addAction("Copy Selection")
        settings_action = menu.addAction("Table Settings...")
        stats_test_action = menu.addAction("Run Statistical Test...")

        action = menu.exec(self.data_table.viewport().mapToGlobal(position))

        if action == resize_cols_action:
            self.data_table.resizeColumnsToContents()
        elif action == resize_rows_action:
            self.data_table.resizeRowsToContents()
        elif action == copy_action:
            self.copy_selection()
        elif action == settings_action:
            self.open_table_customization()
        elif action == stats_test_action:
            self.controller.run_statistical_test_from_selection()
        
    def copy_selection(self) -> None:
        """
        Copies the currently selected cells in the table to the system clipboard
        Formats the copied data as TSV 
        """
        if self.data_table is None:
            return
        
        selection_model = self.data_table.selectionModel()
        if selection_model is None or not selection_model.hasSelection():
            self.status_bar.log("No cells selected to copy", "WARNING")
            return
        
        selected_indexes = selection_model.selectedIndexes()
        if not selected_indexes:
            return
        
        sorted_indexes = sorted(selected_indexes, key=lambda idx: (idx.row(), idx.column()))
        
        copied_text = ""
        previous_row = sorted_indexes[0].row()
        
        for index in sorted_indexes:
            current_row = index.row()
            
            if current_row != previous_row:
                copied_text += "\n"
                previous_row = current_row
            elif index != sorted_indexes[0]:
                copied_text += "\t"
            
            cell_data = index.data(Qt.ItemDataRole.DisplayRole)
            copied_text += str(cell_data) if cell_data is not None else ""
            
        QApplication.clipboard().setText(copied_text)
        self.status_bar.log(f"Copied {len(selected_indexes)} cell(s) to clipboard", "SUCCESS")

    def open_table_customization(self):
        """Opens the settings dialog for the table customzation"""
        if self.data_handler.df is None:
            return

        # Get the current settings
        current_font = self.data_table.font()
        current_font_size = current_font.pointSize()
        if current_font_size <= 0:
            current_font_size = 10

        current_alt_color = (
            self.data_table.palette().color(QPalette.ColorRole.AlternateBase).name()
        )

        current_settings = {
            "alternating_rows": self.data_table.alternatingRowColors(),
            "alt_color": current_alt_color,
            "show_grid": self.data_table.showGrid(),
            "grid_color": getattr(self, "current_grid_color", "#D3D3D3"),
            "grid_style": getattr(self, "current_grid_style", "Solid Line"),
            "show_h_headers": self.data_table.horizontalHeader().isVisible(),
            "show_v_headers": self.data_table.verticalHeader().isVisible(),
            "font_family": current_font.family(),
            "font_size": current_font_size,
            "word_wrap": self.data_table.wordWrap(),
            "selection_behavior": self.data_table.selectionBehavior(),
            "float_precision": self.current_precision,
            "thousands_separator": getattr(self, "current_thousands_sep", False),
            "scientific_notation": getattr(self, "current_scientific_notation", False),
            "nan_display": getattr(self, "current_nan_display", "NaN"),
            "conditional_rules": self.current_formatting_rules,
            "text_alignment": getattr(self, "current_text_alignment", "Left"),
            "render_bools_as_checkboxes": getattr(self, "current_render_bools", True)
        }

        dialog = TableCustomizationDialog(current_settings, self)
        dialog.settings_applied.connect(self.apply_table_settings)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_table_settings(settings)
    
    def apply_table_settings(self, settings: dict) -> None:
        """
        Applies a dictionary of customization settings to the data table and its model.
        Used for both live previewing (Apply) and final confirmation (OK).
        """
        self.current_precision = settings.get("float_precision", 2)
        self.current_formatting_rules = settings.get("conditional_rules", [])
        
        self.current_text_alignment = settings.get("text_alignment", "Left")
        self.current_render_bools = settings.get("render_bools_as_checkboxes", True)

        self.current_nan_display = settings.get("nan_display", "NaN")
        self.current_thousands_sep = settings.get("thousands_separator", False)
        self.current_scientific_notation = settings.get("scientific_notation", False)

        self.current_grid_style = settings.get("grid_style", "Solid Line")
        self.current_grid_color = settings.get("grid_color", "#D3D3D3")

        self.data_table.setAlternatingRowColors(settings["alternating_rows"])
        if settings["alternating_rows"]:
            palette = self.data_table.palette()
            palette.setColor(
                QPalette.ColorRole.AlternateBase, QColor(settings["alt_color"])
            )
            self.data_table.setPalette(palette)
        self.data_table.setShowGrid(settings["show_grid"])
        pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine
        if self.current_grid_style == "Dash Line":
            pen_style = Qt.PenStyle.DashLine
        elif self.current_grid_style == "Dot Line":
            pen_style = Qt.PenStyle.DotLine
        self.data_table.setGridStyle(pen_style)

        if settings.get("show_grid"):
            grid_qcolor: QColor = QColor(self.current_grid_color)
            if grid_qcolor.isValid():
                palette = self.data_table.palette()
                palette.setColor(QPalette.ColorRole.Mid, grid_qcolor)
                self.data_table.setPalette(palette)

        self.data_table.horizontalHeader().setVisible(settings["show_h_headers"])
        self.data_table.verticalHeader().setVisible(settings["show_v_headers"])

        font = QFont(settings["font_family"])
        font.setPointSize(settings["font_size"])
        self.data_table.setFont(font)

        self.data_table.setWordWrap(settings["word_wrap"])
        self.data_table.setSelectionBehavior(settings["selection_behavior"])

        self.data_table.resizeRowsToContents()
        if settings["word_wrap"]:
            self.data_table.resizeColumnsToContents()
        
        if self.data_table.model() and isinstance(self.data_table.model(), DataTableModel):
            self.data_table.model().set_float_precision(self.current_precision)
            self.data_table.model().set_conditional_rules(self.current_formatting_rules)
            self.data_table.model().set_bool_render_style(self.current_render_bools)

            if hasattr(self.data_table.model(), "set_nan_display"):
                self.data_table.model().set_nan_display(self.current_nan_display)
            if hasattr(self.data_table.model(), "set_thousands_separator"):
                self.data_table.model().set_thousands_separator(self.current_thousands_sep)
            if hasattr(self.data_table.model(), "set_scientific_notation"):
                self.data_table.model().set_scientific_notation(self.current_scientific_notation)

            self.data_table.model().layoutChanged.emit()

        self.status_bar.log("Table settings updated", "SUCCESS")

    def get_selection_state(self):
        """Returns the currently selected row indicies and column names"""
        if self.data_table is None or self.data_table.selectionModel() is None:
            return [], []
        
        indexes = self.data_table.selectionModel().selectedIndexes()
        if not indexes:
            return [], []
        
        selected_rows = sorted(list(set(index.row() for index in indexes)))
        if self.data_handler.df is not None:
            col_indices = sorted(list(set(index.column() for index in indexes)))
            selected_columns = []
            for i in col_indices:
                if i < len(self.data_handler.df.columns):
                    selected_columns.append(self.data_handler.df.columns[i])
        else:
            selected_columns = []
        
        return selected_rows, selected_columns
    
    def set_test_results_greeting(self):
        """Sets the initial instructions for the Test Results tab"""
        try:
            greeting_path = Path.cwd() / "resources" / "stats_test_result_greeting.html"
            if greeting_path.exists():
                with open(greeting_path, "r", encoding="utf-8") as file:
                    greeting_html = file.read()
            else:
                greeting_html = "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'><h2>Statistical Test Suite</h2><p>Test Results will appear here.</p></div>"
        except Exception as ReadGreetingError:
            self.status_bar.log(f"Failed to load greeting HTML: {str(ReadGreetingError)}", "ERROR")
            greeting_html = "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'><h2>Statistical Test Suite</h2></div>"
            
        if hasattr(self, 'test_results_text') and self.test_results_text is not None:
            self.test_results_text.setHtml(greeting_html)