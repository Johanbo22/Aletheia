import logging

from PyQt6.QtCore import QModelIndex, QSettings, QSortFilterProxyModel, QTimer, QUrl, Qt
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QKeySequence, QShortcut, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, \
    QSplitter, QTextBrowser, QTreeView, QVBoxLayout, QWidget

from core.help_manager import HelpManager, HelpTopicDetail
from icons.icon_registry import IconBuilder, IconType
from resources.version import APPLICATION_NAME
from ui.help_animation_engine import load_help_animation_widget

logger = logging.getLogger(__name__)

class HelpExplorerDialog(QDialog):
    """
    Help explorer to provide searchable
    documentation of embedded tools
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.help_manager = HelpManager()
        self.current_link: str | None = None

        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(250)

        if parent is None:
            self.setWindowFlags(
                self.windowFlags()
                | Qt.WindowType.Window
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowMinimizeButtonHint
            )

        self.setWindowTitle(f"{APPLICATION_NAME} Help Explorer")
        self.setMinimumSize(1450, 850)
        self.setObjectName("helpExplorerDialog")

        self._init_ui()
        self._setup_models()
        self._connect_signals()
        self._load_topics()

        self.search_input.setFocus()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setObjectName("helpSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Left side with topics and search bar
        self.left_pane = QFrame()
        self.left_pane.setObjectName("helpLeftPane")
        self.left_pane.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(self.left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.search_container = QFrame()
        self.search_container.setObjectName("helpSearchContainer")
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(12, 8, 12, 8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("helpSearchInput")
        self.search_input.setPlaceholderText("Search topics...")
        self.search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_input)

        self.topic_tree = QTreeView()
        self.topic_tree.setObjectName("helpTopicTree")
        self.topic_tree.setHeaderHidden(True)
        self.topic_tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.topic_tree.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.topic_tree.setIndentation(15)
        self.topic_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        left_layout.addWidget(self.search_container)
        left_layout.addWidget(self.topic_tree)

        # right side wiht content
        self.right_pane = QFrame()
        self.right_pane.setObjectName("helpRightPane")
        self.right_pane.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(self.right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # splitter for text / animation area
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal, self.right_pane)
        self.content_splitter.setObjectName("helpContentSplitter")
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Text area
        self.content_text_pane = QFrame()
        self.content_text_pane.setObjectName("helpContentTextPane")
        content_text_layout = QVBoxLayout(self.content_text_pane)
        content_text_layout.setContentsMargins(30, 30, 15, 30)
        content_text_layout.setSpacing(20)

        self.title_label = QLabel("Select a topic to view details")
        self.title_label.setObjectName("helpTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.title_label.setWordWrap(True)

        self.content_browser = QTextBrowser()
        self.content_browser.setObjectName("helpContentBrowser")
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.link_button = QPushButton("Read More")
        self.link_button.setIcon(IconBuilder.build(IconType.Help))
        self.link_button.setVisible(False)
        self.link_button.setCursor(Qt.CursorShape.PointingHandCursor)

        content_text_layout.addWidget(self.title_label)
        content_text_layout.addWidget(self.content_browser)
        content_text_layout.addWidget(self.link_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Animation area
        self.content_animation_pane = QFrame()
        self.content_animation_pane.setObjectName("helpContentAnimationPane")
        content_animation_layout = QVBoxLayout(self.content_animation_pane)
        content_animation_layout.setContentsMargins(15, 30, 30, 30)
        content_animation_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_animation_pane.setVisible(False)

        self.animation_container = QWidget()
        self.animation_layout = QVBoxLayout(self.animation_container)
        self.animation_layout.setContentsMargins(0, 0, 0, 0)
        self.animation_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_animation_widget: QWidget | None = None

        content_animation_layout.addWidget(self.animation_container)

        self.content_splitter.addWidget(self.content_text_pane)
        self.content_splitter.addWidget(self.content_animation_pane)
        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(self.content_splitter)

        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.right_pane)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)

        main_layout.addWidget(self.splitter)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        main_layout.addWidget(self.button_box)

        self._read_settings()

    def _setup_models(self) -> None:
        self.source_model = QStandardItemModel(self)

        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)

        self.proxy_model.setRecursiveFilteringEnabled(True)

        self.topic_tree.setModel(self.proxy_model)

    def _connect_signals(self) -> None:
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self._search_debounce_timer.timeout.connect(self._apply_search_filter)
        self.topic_tree.selectionModel().currentChanged.connect(self._on_current_changed)
        self.link_button.clicked.connect(self._open_external_link)

        self.button_box.rejected.connect(self.reject)

        self.search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.search_shortcut.activated.connect(self.search_input.setFocus)
        self.search_shortcut.activated.connect(self.search_input.selectAll)

    def _on_search_text_changed(self) -> None:
        """Triggers the debounce timer for search filtering"""
        self._search_debounce_timer.start()

    def _apply_search_filter(self) -> None:
        """Applies the filter to the proxy model and automatically expands the tree if filtering"""
        search_text = self.search_input.text()
        self.proxy_model.setFilterFixedString(search_text)

        if search_text:
            self.topic_tree.collapseAll()
            self.topic_tree.expandToDepth(0)

    def _load_topics(self) -> None:
        grouped_topics = self.help_manager.get_all_help_topics()

        for category, topics in grouped_topics.items():
            parent_item = QStandardItem(category)
            parent_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

            for topic in topics:
                child_item = QStandardItem(topic["title"])
                child_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                child_item.setData(topic["topic_id"], Qt.ItemDataRole.UserRole)
                parent_item.appendRow(child_item)

            self.source_model.appendRow(parent_item)

        self.topic_tree.expandAll()

    def _on_current_changed(self, current: QModelIndex) -> None:
        if not current.isValid():
            self._clear_detail_pane()
            return

        source_index = self.proxy_model.mapToSource(current)
        topic_id: str | None = self.source_model.data(source_index, Qt.ItemDataRole.UserRole)

        if not topic_id:
            category_name = self.source_model.data(source_index, Qt.ItemDataRole.DisplayRole)
            self._clear_detail_pane(
                title=f"Category: {category_name}",
                content="Expand and select a specific topic below to view its details and animations"
            )
            is_expanded = self.topic_tree.isExpanded(current)
            self.topic_tree.setExpanded(current, not is_expanded)
            return

        detail_data: HelpTopicDetail | None = self.help_manager.get_detailed_help_topic(topic_id)
        if detail_data:
            self._update_detail_pane(detail_data)
        else:
            logger.warning(f"Failed to load the detailed data for topic ID: {topic_id}")
            self._clear_detail_pane()

    def _update_detail_pane(self, detail: HelpTopicDetail) -> None:
        self.title_label.setText(detail.title)
        self.title_label.setObjectName("HelpDialogTitle")

        if self.current_animation_widget:
            self.animation_layout.removeWidget(self.current_animation_widget)
            self.current_animation_widget.deleteLater()
            self.current_animation_widget = None

        self.current_animation_widget = load_help_animation_widget(detail.topic_id)
        if self.current_animation_widget:
            self.animation_layout.addWidget(self.current_animation_widget)
            self.content_animation_pane.setVisible(True)
        else:
            self.content_animation_pane.setVisible(False)

        content: str = detail.detailed_description if detail.detailed_description else detail.description
        self.content_browser.setMarkdown(content)

        self.current_link = detail.link
        self.link_button.setVisible(bool(detail.link))
        if detail.link:
            self.link_button.setToolTip(f"{detail.link}")
        else:
            self.link_button.setToolTip("")

    def _clear_detail_pane(self, title: str = "Select a topic to view details", content: str = "") -> None:
        self.title_label.setText(title)

        if self.current_animation_widget:
            self.animation_layout.removeWidget(self.current_animation_widget)
            self.current_animation_widget.deleteLater()
            self.current_animation_widget = None

        self.content_animation_pane.setVisible(False)
        self.content_browser.setMarkdown(content)
        self.current_link = None
        self.link_button.setVisible(False)
        self.link_button.setToolTip("")

    def _open_external_link(self) -> None:
        if self.current_link:
            logger.info(f"Opening link: {self.current_link}")
            QDesktopServices.openUrl(QUrl(self.current_link))

    def _read_settings(self) -> None:
        """Restores the window geometry and splitter sizes from the last session"""
        settings = QSettings(f"{APPLICATION_NAME}", "HelpExplorer")

        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        splitter_state = settings.value("splitterState")
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        content_splitter_state = settings.value("contentSplitterState")
        if content_splitter_state:
            self.content_splitter.restoreState(content_splitter_state)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Saves the window geometry and splitter sizes before closing"""
        settings = QSettings(f"{APPLICATION_NAME}", "HelpExplorer")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("splitterState", self.splitter.saveState())
        settings.setValue("contentSplitterState", self.content_splitter.saveState())
        super().closeEvent(event)

    def navigate_to_topic(self, topic_id: str) -> None:
        """
        Finds the given topic in the tree and selects it.

        :param topic_id: The identifier of the topic to navigate to
        """
        if not topic_id:
            return

        if self.search_input.text():
            self.search_input.clear()

        for row in range(self.source_model.rowCount()):
            parent_item = self.source_model.item(row)
            if not parent_item:
                continue

            for child_row in range(parent_item.rowCount()):
                child_item = parent_item.child(child_row)
                if child_item and child_item.data(Qt.ItemDataRole.UserRole) == topic_id:
                    source_index = child_item.index()
                    proxy_index = self.proxy_model.mapFromSource(source_index)

                    if proxy_index.isValid():
                        self.topic_tree.setCurrentIndex(proxy_index)
                        self.topic_tree.scrollTo(proxy_index)
                    return
