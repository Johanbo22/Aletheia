# ui/data_tab.py
import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QEasingCurve, QItemSelectionModel, QPropertyAnimation, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QPalette, QShortcut
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QAbstractItemView, QGraphicsOpacityEffect, QHBoxLayout, QHeaderView, \
    QListWidgetItem, QSplitter, QStackedWidget, QTabWidget, QTableView, QVBoxLayout, QWidget
from pandas import DataFrame

from controller.data_tab_controller import DataTabController
from core.data_handler import DataHandler
from core.global_signals import ToastLevel, global_signals
from core.subset_manager import SubsetManager
from icons import IconBuilder, IconType
from ui.LandingPage import LandingPage
from ui.animations import EditModeToggleAnimation
from ui.components.data_operations_panel import DataOperationsPanel
from ui.components.data_search_bar import DataSearchBar
from ui.components.data_table_delegate import DataTableDelegate
from ui.components.data_view_toolbar import DataViewToolbar
from ui.components.main_data_table_view import MainDataTableView
from ui.components.statistics_generator import StatisticsGenerator
from ui.data_table_model import DataTableModel
from ui.dialogs import TableCustomizationDialog
from ui.models.table_settings_state import TableSettingsState
from ui.status_bar import LogLevel, StatusBar
from ui.theme import ThemeColors

logger = logging.getLogger(__name__)

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
    request_switch_to_plot = pyqtSignal()
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
        self.controller = DataTabController(data_handler=self.data_handler, status_bar=self.status_bar, view=self,
                                            subset_manager=self.subset_manager)
        self.stats_generator = StatisticsGenerator()
        self.plot_tab = None
        self.data_table = None
        self.stats_text = None
        self.data_tabs = None
        self.subset_view_label = None
        self.aggregation_view_label = None
        self.is_editing = False

        self.table_settings = TableSettingsState()

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
        main_layout: QHBoxLayout | QHBoxLayout = QHBoxLayout(self)

        left_widget: QWidget | QWidget = self._setup_left_panel()
        right_widget: QWidget | QWidget = self._setup_right_panel()

        splitter: QSplitter | QSplitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.refresh_data_view()

    def _setup_left_panel(self) -> QWidget:
        """Sets up the left panel containing the landing page and data views"""
        left_widget: QWidget | QWidget = QWidget()
        left_layout: QVBoxLayout | QVBoxLayout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.left_stack = QStackedWidget()
        left_layout.addWidget(self.left_stack)

        self._setup_landing_page()
        self._setup_data_view_container()

        return left_widget

    def _setup_landing_page(self) -> None:
        """Initializes the landing page and its signals"""
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

    def _setup_data_view_container(self) -> None:
        """Sets up the container for the data view widgets"""
        self.data_view_widget = QWidget()
        data_view_layout: QVBoxLayout | QVBoxLayout = QVBoxLayout(self.data_view_widget)
        data_view_layout.setContentsMargins(0, 0, 0, 0)
        data_view_layout.setSpacing(6)
        self.left_stack.addWidget(self.data_view_widget)

        self._setup_toolbar_and_search(data_view_layout)
        self._setup_data_tabs(data_view_layout)

    def _setup_toolbar_and_search(self, layout: QVBoxLayout) -> None:
        """Sets up the toolbar and search bar"""
        # Data toolbar
        self.toolbar = DataViewToolbar(parent=self)
        self.toolbar.create_dataset_requested.connect(self.controller.create_new_dataset)
        self.toolbar.refresh_data_requested.connect(self.controller.refresh_google_sheets)
        self.toolbar.python_console_requested.connect(self.request_python_console.emit)
        self.toolbar.edit_mode_toggled.connect(self.toggle_edit_mode)
        layout.addWidget(self.toolbar)

        # Search bar
        self.search_bar = DataSearchBar(data_handler=self.data_handler, parent=self)
        self.search_bar.match_found.connect(self.highlight_cell)
        self.search_bar.clear_selection_requested.connect(
            lambda: self.data_table.clearSelection() if self.data_handler else None)

        self.search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.search_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.search_shortcut.activated.connect(self.open_search_bar)

        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self.search_bar)
        self.esc_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.esc_shortcut.activated.connect(self.search_bar.close_search)

        layout.addWidget(self.search_bar)

    def _setup_data_tabs(self, layout: QVBoxLayout) -> None:
        """Creates the tab widget for data and statistics"""
        self.data_tabs = QTabWidget()
        self._setup_data_table()
        self._setup_stats_and_test_tabs()
        layout.addWidget(self.data_tabs, 1)

    def _setup_data_table(self) -> None:
        """Configures the main data table view"""
        self.data_table = MainDataTableView(self.status_bar, self.data_handler, self)

        self.table_delegate = DataTableDelegate(self.data_table)
        self.data_table.setItemDelegate(self.table_delegate)
        self.data_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.data_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)

        self.data_table.doubleClicked.connect(self._on_table_double_clicked)

        palette: QPalette = self.data_table.palette()
        active_highlight: QColor | Any = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight)
        active_text: QColor | Any = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, active_highlight)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, active_text)
        self.data_table.setPalette(palette)

        self.data_table.request_table_settings.connect(self.open_table_customization)
        self.data_table.request_statistical_test.connect(self.controller.run_statistical_test_from_selection)

        data_table_icon: QIcon | QIcon = IconBuilder.build(IconType.DataExplorerIcon)
        self.data_tabs.addTab(self.data_table, data_table_icon, "Data Table")

    def _setup_stats_and_test_tabs(self) -> None:
        """Sets up the statistics and test results web engine view tabs"""
        # Statistics tab
        self.stats_text = QWebEngineView()
        self.stats_text.page().setBackgroundColor(QColor(Qt.GlobalColor.transparent))

        self.stats_opacity_effect = QGraphicsOpacityEffect(self.stats_text)
        self.stats_text.setGraphicsEffect(self.stats_opacity_effect)
        stats_icon: QIcon | QIcon = IconBuilder.build(IconType.ExploreStatisticsIcon)
        self.data_tabs.addTab(self.stats_text, stats_icon, "Statistics")

        # Test results tab
        self.test_results_text = QWebEngineView()
        self.test_results_text.page().setBackgroundColor(Qt.GlobalColor.transparent)

        self.set_test_results_greeting()
        test_result_icon: QIcon | QIcon = IconBuilder.build(IconType.Calculator)
        self.data_tabs.addTab(self.test_results_text, test_result_icon, "Test Results")

    def _setup_right_panel(self) -> QWidget:
        """Sets up the right side operations panel"""
        right_widget: QWidget | QWidget = QWidget()
        right_layout: QVBoxLayout | QVBoxLayout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.operations_panel = DataOperationsPanel(parent=self, controller=self.controller)

        right_layout.addWidget(self.operations_panel)
        self.right_widget = right_widget

        return right_widget

    def _on_table_double_clicked(self) -> None:
        """
        Guidance if trying to edit without edit mode enabled
        DataTable.EditTrigger is set to NoEditTriggers to avoid unintentional data changes
        """
        if not self.is_editing:
            global_signals.request_toast("Read-Only Mode", "Enable Edit Mode in the toolbar to modify cell values",
                                         ToastLevel.INFO)

    def toggle_edit_mode(self, is_editing: bool) -> None:
        """
        Toggles the edit mode in the data table based on toolbar state
        """
        self.is_editing = is_editing

        if self.is_editing:
            self.data_table.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed)
            self.status_bar.log("Edit Mode Enabled. You are now able to edit cells in the data table", LogLevel.INFO)

            EditModeToggleAnimation(parent=self, is_on=True).start(target_widget=self)
        else:
            self.data_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
            self.status_bar.log("Edit Mode Disabled", LogLevel.INFO)
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
            self.data_table.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
            self.data_table.setCurrentIndex(index)
            self.data_table.scrollTo(index, QTableView.ScrollHint.PositionAtCenter)
            self.data_table.setFocus()

    def refresh_data_view(self, reload_model: bool = True):
        """Refresh the data table and statistics"""
        if self.data_handler.df is None:
            self._handle_empty_data_view()
            return

        # Detect if a completely new dataset or project has been loaded
        history_info: dict[str, Any] = self.data_handler.get_history_info()
        nodes_dict: dict[Any, Any] = history_info.get("nodes", {})
        root_id: Any | None = history_info.get("root_id")
        root_node: Any | None = nodes_dict.get(root_id)

        dataset_signature: str = f"{id(root_node)}_{getattr(self.data_handler, 'file_path', '')}_{getattr(self.data_handler, 'last_gsheet_gid', '')}"
        if getattr(self, "_last_dataset_signature", None) != dataset_signature:
            if not hasattr(self.data_handler, "test_results_history") or not self.data_handler.test_results_history:
                self.set_test_results_greeting()
                if not hasattr(self, "data_tabs") or self.data_tabs is None:
                    return
                self.data_tabs.setCurrentIndex(0)
            else:
                controller = getattr(self, "controller", None)
                if not controller or not hasattr(controller, "_render_test_results_page"):
                    return
                controller._render_test_results_page()
            self._last_dataset_signature = dataset_signature

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

        if hasattr(self, "test_results_text") and self.test_results_text is not None:
            self.set_test_results_greeting()

        if hasattr(self, "toolbar"):
            self.toolbar.set_refresh_visible(False)

        self.status_bar.set_data_source("")
        self.status_bar.set_view_context("", "normal")

        self._last_dataset_signature = None
        if hasattr(self, "data_tabs") and self.data_tabs is not None:
            self.data_tabs.setCurrentIndex(0)

    def _update_data_model(self, reload_model: bool) -> None:
        """Updates the table model and restores sorting states"""
        if not reload_model:
            return

        df: DataFrame | None = self.data_handler.df
        if not hasattr(self, "model") or not isinstance(self.model, DataTableModel):
            self.model = DataTableModel(
                self.data_handler,
                editable=self.is_editing,
                float_precision=self.table_settings.precision,
                conditional_rules=self.table_settings.formatting_rules
            )
            self.model.set_bool_render_style(self.table_settings.render_bools)
            self.model.set_nan_display(self.table_settings.nan_display)
            self.model.set_thousands_separator(self.table_settings.thousands_sep)
            self.model.set_scientific_notation(self.table_settings.scientific_notation)

            self.model.columnsInserted.connect(self._update_column_selectors)
            self.data_table.setSortingEnabled(False)
            self.data_table.setModel(self.model)
        else:
            self.model.update_data()
            self.data_table.setSortingEnabled(False)

            if self.data_table.model() is self.model:
                return
            self.data_table.setModel(self.model)

        header = self.data_table.horizontalHeader()
        header.blockSignals(True)

        if not self.data_handler.sort_state:
            header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        else:
            col_name, ascending = self.data_handler.sort_state
            try:
                col_index = list(df.columns).index(col_name)
                order = (Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder)
                header.setSortIndicator(col_index, order)
            except ValueError:
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
        df: DataFrame | None = self.data_handler.df
        columns: list[Any] = list(df.columns)
        panel: DataOperationsPanel = self.operations_panel

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
            panel.transform_tab.sort_column_combo.addItem("[Index]")
            panel.transform_tab.sort_column_combo.addItems(columns)
            if current_sort and (current_sort == "[Index]" or current_sort in columns):
                panel.transform_tab.sort_column_combo.setCurrentText(current_sort)
            elif self.data_handler.sort_state and self.data_handler.sort_state[0] in columns:
                panel.transform_tab.sort_column_combo.setCurrentText(self.data_handler.sort_state[0])
            elif self.data_handler.sort_state and self.data_handler.sort_state[0] is None:
                panel.transform_tab.sort_column_combo.setCurrentText("[Index]")

        if hasattr(panel, "subsets_tab") and hasattr(panel.subsets_tab, "subset_column_combo"):
            try:
                panel.subsets_tab.subset_column_combo.clear()
                panel.subsets_tab.subset_column_combo.addItems(columns)
            except Exception as Error:
                logger.warning(f"Could not update subset columns: {Error}")
                self.status_bar.log(f"Warning: Could not update subset columns: {Error}", LogLevel.WARNING)

        if not self.plot_tab:
            return
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
            logger.warning(f"Could not refresh subsets: {Error}")
            self.status_bar.log(f"Warning: Could not refresh subsets: {Error}", LogLevel.WARNING)

        inserted_name: Any | None = getattr(self.data_handler, "inserted_subset_name", None)
        agg_name: Any | None = getattr(self.data_handler, "viewing_aggregation_name", None)

        if agg_name:
            self.status_bar.set_view_context(f"Viewing Aggregation: {agg_name}")
        elif inserted_name:
            self.status_bar.set_view_context(f"Viewing Subset: {inserted_name}")
        else:
            self.status_bar.set_view_context("", "normal")

    def _update_history_list(self) -> None:
        """Updates the history list and pipeline graph for the branching tree system."""
        panel: DataOperationsPanel = self.operations_panel
        if not hasattr(panel, "history_tab") or not hasattr(panel.history_tab, "history_list"):
            return

        panel.history_tab.history_list.clear()

        history_information: dict[str, Any] = self.data_handler.get_history_info()
        nodes_dict: dict[Any, Any] = history_information.get("nodes", {})
        current_node_id: Any | None = history_information.get("current_node_id")
        root_id: Any | None = history_information.get("root_id")

        if not nodes_dict or not current_node_id or not root_id:
            return

        for node in nodes_dict.values():
            if not node.diff_record or "type" in node.diff_record.metadata:
                continue
            node.diff_record.metadata["type"] = node.diff_record.operation_type.value

        path_to_current: list[Any | None] = []
        curr: Any | None = current_node_id
        while curr:
            path_to_current.append(curr)
            curr = nodes_dict[curr].parent_id if curr in nodes_dict else None
        path_to_current.reverse()

        item_height: int = 32

        def style_item(item: QListWidgetItem, is_active: bool, text: str) -> None:
            item.setSizeHint(QSize(0, item_height))
            font: QFont | None = item.font()
            font.setPointSize(9)

            if not is_active:
                item.setText(text)
                font.setWeight(QFont.Weight.Medium)
                item.setFont(font)
                item.setForeground(QColor("#334155"))
            else:
                item.setText(f"{text}  ← Active")
                font.setWeight(QFont.Weight.Bold)
                item.setFont(font)
                try:
                    active_color: QColor | QColor = QColor(ThemeColors.MainColor)
                    bg_color: QColor | QColor = QColor(ThemeColors.MainColor)
                    bg_color.setAlpha(25)
                except Exception:
                    active_color = QColor("#2563eb")
                    bg_color = QColor("#dbeafe")
                item.setForeground(active_color)
                item.setBackground(bg_color)

        initial_item: QListWidgetItem | QListWidgetItem = QListWidgetItem("0. Initial Data")
        initial_item.setData(Qt.ItemDataRole.UserRole, root_id)
        initial_item.setIcon(IconBuilder.build(IconType.DataExplorerIcon))
        initial_item.setToolTip("The original data state upon import or creation")
        style_item(initial_item, root_id == current_node_id, "0. Initial Data")
        panel.history_tab.history_list.addItem(initial_item)

        for i, node_id in enumerate(path_to_current):
            if node_id == root_id:
                continue

            node = nodes_dict[node_id]
            operation = node.diff_record.metadata
            operation_type = operation.get("type", "Unknown")
            operation_text: str = self._format_operation_text(operation)

            item: QListWidgetItem | QListWidgetItem = QListWidgetItem(f"{i}. {operation_text}")
            item.setData(Qt.ItemDataRole.UserRole, node_id)
            item.setIcon(self._get_icon_for_operation(operation_type))

            details: str = "".join(
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
        self.request_switch_to_plot.emit()

    def update_statistics(self) -> None:
        """Update statistics display"""
        if self.data_handler.df is None:
            return

        try:
            info: dict[str, Any] = self.data_handler.get_data_info()
            df: DataFrame = self.data_handler.df
        except Exception as UpdateStatisticsError:
            self.stats_text.setHtml(
                f"<p style='color: red;'>Error loading data info: {str(UpdateStatisticsError)}</p>"
            )
            return

        # Generate HTML
        final_html: str = self.stats_generator.generate_html(df, info)
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
        if hasattr(self, "model"):
            del self.model
        self.stats_text.setHtml("")
        if hasattr(self, "test_results_text"):
            self.set_test_results_greeting()

        if hasattr(self, "toolbar"):
            self.toolbar.set_refresh_visible(False)
        self.status_bar.set_data_source("")
        self.status_bar.set_view_context("", "normal")

        self._last_dataset_signature = None
        if hasattr(self, "data_tabs") and self.data_tabs is not None:
            self.data_tabs.setCurrentIndex(0)

    def _format_operation_text(self, operation: dict) -> str:
        """Formatter for operation dict back to better text handling"""
        operation_type: str = operation.get("type", "Unknown")

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
                col: str = operation.get("column", "All Columns")
                return f"Fill missing: {col} ({operation.get('method')})"
            case "drop_missing":
                return "Drop missing Values"
            case "drop_duplicates":
                return "Remove Duplicate Values"
            case "aggregate":
                group_by: list[Any] = operation.get("group_by", [])
                return f"Aggregate: Grouped by {len(group_by)} cols"
            case "melt":
                return "Melt/Unpivot Data"
            case "pivot":
                index_cols: list[Any] = operation.get("index", [])
                return f"Pivot Table (Index: {index_cols})"
            case "merge":
                return f"Merge Data ({operation.get('how', 'inner')})"
            case "concatenate":
                return "Append / Concatenate Data"
            case "sort":
                direction: str = "Asc" if operation.get("ascending") else "Desc"
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
                rows: list[Any] = operation.get("rows", [])
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
            "alternating_rows"          : self.data_table.alternatingRowColors(),
            "alt_color"                 : current_alt_color,
            "show_grid"                 : self.data_table.showGrid(),
            "grid_color"                : self.table_settings.grid_color,
            "grid_style"                : self.table_settings.grid_style,
            "show_h_headers"            : self.data_table.horizontalHeader().isVisible(),
            "show_v_headers"            : self.data_table.verticalHeader().isVisible(),
            "font_family"               : current_font.family(),
            "font_size"                 : current_font_size,
            "word_wrap"                 : self.data_table.wordWrap(),
            "selection_behavior"        : self.data_table.selectionBehavior(),
            "float_precision"           : self.table_settings.precision,
            "thousands_separator"       : self.table_settings.thousands_sep,
            "scientific_notation"       : self.table_settings.scientific_notation,
            "nan_display"               : self.table_settings.nan_display,
            "conditional_rules"         : self.table_settings.formatting_rules,
            "text_alignment"            : self.table_settings.text_alignment,
            "render_bools_as_checkboxes": self.table_settings.render_bools
        }

        dialog: TableCustomizationDialog = TableCustomizationDialog(current_settings, self)
        dialog.settings_applied.connect(self.apply_table_settings)
        if not dialog.exec():
            return
        settings: dict = dialog.get_settings()
        self.apply_table_settings(settings)

    def apply_table_settings(self, settings: dict) -> None:
        """
        Applies a dictionary of customization settings to the data table and its model.
        Used for both live previewing (Apply) and final confirmation (OK).
        """
        self.table_settings.precision = settings.get("float_precision", 2)
        self.table_settings.formatting_rules = settings.get("conditional_rules", [])
        self.table_settings.text_alignment = settings.get("text_alignment", "Left")
        self.table_settings.render_bools = settings.get("render_bools_as_checkboxes", True)
        self.table_settings.nan_display = settings.get("nan_display", "NaN")
        self.table_settings.thousands_sep = settings.get("thousands_separator", False)
        self.table_settings.scientific_notation = settings.get("scientific_notation", False)
        self.table_settings.grid_style = settings.get("grid_style", "Solid Line")
        self.table_settings.grid_color = settings.get("grid_color", "#D3D3D3")

        self.data_table.setAlternatingRowColors(settings["alternating_rows"])
        if settings["alternating_rows"]:
            palette = self.data_table.palette()
            palette.setColor(
                QPalette.ColorRole.AlternateBase, QColor(settings["alt_color"])
            )
            self.data_table.setPalette(palette)

        self.data_table.setShowGrid(settings["show_grid"])
        pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine
        if self.table_settings.grid_style == "Dash Line":
            pen_style = Qt.PenStyle.DashLine
        elif self.table_settings.grid_style == "Dot Line":
            pen_style = Qt.PenStyle.DotLine
        self.data_table.setGridStyle(pen_style)

        if settings.get("show_grid"):
            grid_qcolor: QColor = QColor(self.table_settings.grid_color)
            if not grid_qcolor.isValid():
                return
            palette = self.data_table.palette()
            palette.setColor(QPalette.ColorRole.Mid, grid_qcolor)
            self.data_table.setPalette(palette)

        self.data_table.horizontalHeader().setVisible(settings["show_h_headers"])
        self.data_table.verticalHeader().setVisible(settings["show_v_headers"])

        font: QFont | QFont = QFont(settings["font_family"])
        font.setPointSize(settings["font_size"])
        self.data_table.setFont(font)

        self.data_table.setWordWrap(settings["word_wrap"])
        self.data_table.setSelectionBehavior(settings["selection_behavior"])

        if settings["word_wrap"]:
            self.data_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.data_table.resizeColumnsToContents()
        else:
            self.data_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            self.data_table.verticalHeader().setDefaultSectionSize(32)

        if self.data_table.model() and isinstance(self.data_table.model(), DataTableModel):
            self.data_table.model().set_float_precision(self.table_settings.precision)
            self.data_table.model().set_conditional_rules(self.table_settings.formatting_rules)
            self.data_table.model().set_bool_render_style(self.table_settings.render_bools)

            self.data_table.model().set_nan_display(self.table_settings.nan_display)
            self.data_table.model().set_thousands_separator(self.table_settings.thousands_sep)
            self.data_table.model().set_scientific_notation(self.table_settings.scientific_notation)

            self.data_table.model().layoutChanged.emit()

        self.status_bar.log("Table settings updated", LogLevel.SUCCESS)

    def get_selection_state(self):
        """Returns the currently selected row indicies and column names"""
        if self.data_table is None or self.data_table.selectionModel() is None:
            return [], []

        indexes = self.data_table.selectionModel().selectedIndexes()
        if not indexes:
            return [], []

        selected_rows = sorted(list(set(index.row() for index in indexes)))
        if self.data_handler.df is None:
            selected_columns = []
        else:
            col_indices = sorted(list(set(index.column() for index in indexes)))
            selected_columns = []
            for i in col_indices:
                if i < len(self.data_handler.df.columns):
                    selected_columns.append(self.data_handler.df.columns[i])

        return selected_rows, selected_columns

    def set_test_results_greeting(self):
        """Sets the initial instructions for the Test Results tab"""
        try:
            greeting_path: Path = Path.cwd() / "resources" / "stats_test_result_greeting.html"
            if not greeting_path.exists():
                greeting_html: str = (
                    "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'>"
                    "<h2>Statistical Test Suite</h2>"
                    "<p>Run a statistical test from the table to see results here.</p>"
                    "</div>"
                )
            else:
                with open(greeting_path, "r", encoding="utf-8") as file:
                    greeting_html = file.read()
        except Exception as ReadGreetingError:
            self.status_bar.log(f"Failed to load greeting HTML: {str(ReadGreetingError)}", LogLevel.ERROR)
            greeting_html = (
                "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'>"
                "<h2>Statistical Test Suite</h2>"
                "<p>Test Results will appear here.</p>"
                "</div>"
            )

        if not hasattr(self, 'test_results_text') or self.test_results_text is None:
            return
        self.test_results_text.setHtml(greeting_html)
