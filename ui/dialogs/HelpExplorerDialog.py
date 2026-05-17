import importlib.util
import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSortFilterProxyModel, QUrl, QModelIndex
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QDesktopServices
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QLineEdit, QTextBrowser, QLabel, QWidget, \
    QFrame, QSizePolicy, QTreeView

from core.help_manager import HelpManager, HelpTopicDetail
from core.resource_loader import get_resource_path
from resources.version import APPLICATION_NAME
from ui.icons.icon_registry import IconBuilder, IconType
from ui.widgets import DataPlotStudioButton

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

        if parent is None:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        
        self.setWindowTitle(f"{APPLICATION_NAME} Help Explorer")
        self.setMinimumSize(1450, 850)
        self.setObjectName("helpExplorerDialog")
        
        self._init_ui()
        self._setup_models()
        self._connect_signals()
        self._load_topics()
        
    def _init_ui(self) -> None:
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setObjectName("helpSplitter")
        self.splitter.setHandleWidth(1)
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
        right_layout.setContentsMargins(30, 30, 30, 30)
        right_layout.setSpacing(20)
        
        self.title_label = QLabel("Select a topic to view details")
        self.title_label.setObjectName("helpTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.title_label.setWordWrap(True)
        
        self.animation_container = QWidget()
        self.animation_layout = QVBoxLayout(self.animation_container)
        self.animation_layout.setContentsMargins(0, 0, 0, 0)
        self.animation_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_animation_widget: QWidget | None = None
        self.animation_container.setVisible(False)
        
        self.content_browser = QTextBrowser()
        self.content_browser.setObjectName("helpContentBrowser")
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.link_button = DataPlotStudioButton("Read More")
        self.link_button.setIcon(IconBuilder.build(IconType.Help))
        self.link_button.setObjectName("helpExternalLinkButton")
        self.link_button.setVisible(False)
        self.link_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        right_layout.addWidget(self.title_label)
        right_layout.addWidget(self.animation_container)
        right_layout.addWidget(self.content_browser)
        right_layout.addWidget(self.link_button)
        
        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.right_pane)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(self.splitter)
    
    def _setup_models(self) -> None:
        self.source_model = QStandardItemModel(self)
        
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)
        
        self.proxy_model.setRecursiveFilteringEnabled(True)
        
        self.topic_tree.setModel(self.proxy_model)
        
    def _connect_signals(self) -> None:
        self.search_input.textChanged.connect(self.proxy_model.setFilterFixedString)
        self.topic_tree.selectionModel().currentChanged.connect(self._on_current_changed)
        self.topic_tree.clicked.connect(self._on_item_clicked)
        self.link_button.clicked.connect(self._open_external_link)
    
    def _on_item_clicked(self, proxy_index: QModelIndex) -> None:
        self._on_current_changed(proxy_index)
    
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
            self._clear_detail_pane()
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
            
        self.current_animation_widget = self._load_animation(detail.topic_id)
        self.animation_layout.addWidget(self.current_animation_widget)
        self.animation_container.setVisible(True)
        
        content: str = detail.detailed_description if detail.detailed_description else detail.description
        self.content_browser.setMarkdown(content)
        
        self.current_link = detail.link
        self.link_button.setVisible(bool(detail.link))
    
    def _clear_detail_pane(self) -> None:
        self.title_label.setText("Select a topic to view details")
        
        if self.current_animation_widget:
            self.animation_layout.removeWidget(self.current_animation_widget)
            self.current_animation_widget.deleteLater()
            self.current_animation_widget = None
        
        self.animation_container.setVisible(False)
        self.content_browser.clear()
        self.current_link = None
        self.link_button.setVisible(False)
    
    def _load_animation(self, topic_id: str) -> QWidget:
        current_dir = Path(__file__).resolve().parent
        ui_dir = current_dir.parent
        project_root = ui_dir.parent
        
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        clean_filename = f"{str(topic_id).lower()}.py"
        anim_path_obj = project_root / "resources" / "help_animations" / clean_filename
        anim_path = get_resource_path(str(anim_path_obj))
        
        if not Path(anim_path).exists():
            logger.debug(f"HelpExplorer: Animation file missing at {anim_path}")
            return self._create_placeholder(f"No animation found for '{topic_id}'")

        try:
            spec = importlib.util.spec_from_file_location(f"anim_{topic_id}", anim_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"anim_{topic_id}"] = module
                spec.loader.exec_module(module)
                
                if hasattr(module, "Animation"):
                    return module.Animation()
        except Exception as err:
            logger.error(f"HelpExplorer: Error loading {anim_path}: {str(err)}")
        
        return self._create_placeholder("Preview unavailable")

    def _create_placeholder(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFixedSize(550, 350)
        lbl.setObjectName("help_animation_placeholder")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl
    
    def _open_external_link(self) -> None:
        if self.current_link:
            logger.info(f"Opening link: {self.current_link}")
            QDesktopServices.openUrl(QUrl(self.current_link))
        