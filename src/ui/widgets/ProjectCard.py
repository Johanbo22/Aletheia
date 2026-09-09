from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QEasingCurve, QEvent, QParallelAnimationGroup, QPoint, QPropertyAnimation, QThreadPool, Qt, \
    pyqtProperty, pyqtSignal
from PyQt6.QtGui import QEnterEvent, QFocusEvent, QFontMetrics, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMenu, QSizePolicy, QVBoxLayout, \
    QWidget

from icons import IconBuilder, IconType
from src.core.project_file_info import ProjectFileMetadata, format_file_size, format_saved_timestamp
from src.ui.workers import ProjectMetadataWorker

class ProjectCard(QFrame):
    """
    A card widget representing one entry in the recent projects list on the Landing page

    Has the same size as the recent project button but has a hoverEvent it expands vertically
    to show statistics about the project.
    Left click opens the project and a right click context menu offers Open, rename, show in file explorer, remove from recents and delete project
    """

    openRequested = pyqtSignal(str)
    renameRequested = pyqtSignal(str)
    revealRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)

    COLLAPSED_HEIGHT: int = 44
    EXPANDED_HEIGHT: int = 132
    ANIMATION_DURATION_MS: int = 160

    def __init__(self, file_path: str, width: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_path: str = file_path

        self._metadata: Optional[ProjectFileMetadata] = None
        self._metadata_requested: bool = False
        self._hovered: bool = False
        self._focused: bool = False

        self.setObjectName("ProjectCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("cardState", "normal")
        self.setFixedWidth(width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._build_ui(width)

        self._card_height: int = self.COLLAPSED_HEIGHT
        self.setFixedHeight(self.COLLAPSED_HEIGHT)

        self._opacity_effect = QGraphicsOpacityEffect(self._details_container)
        self._opacity_effect.setOpacity(0.0)
        self._details_container.setGraphicsEffect(self._opacity_effect)

        self._animation_group = QParallelAnimationGroup(self)

        self._height_animation = QPropertyAnimation(self, b"cardHeight")
        self._height_animation.setDuration(self.ANIMATION_DURATION_MS)
        self._height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._opacity_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._opacity_animation.setDuration(self.ANIMATION_DURATION_MS)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._animation_group.addAnimation(self._height_animation)
        self._animation_group.addAnimation(self._opacity_animation)

    def _build_ui(self, width: int) -> None:
        file_path = Path(self.file_path)
        parent_dir = file_path.parent.name
        display_name = f"{file_path.name} ({parent_dir})" if parent_dir else file_path.name
        self.setToolTip(str(file_path.absolute()))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(IconBuilder.build(IconType.OpenProject).pixmap(18, 18))
        header_layout.addWidget(icon_label)

        available_width = width - 60
        elided_name = QFontMetrics(self.font()).elidedText(display_name, Qt.TextElideMode.ElideMiddle, available_width)
        self._name_label = QLabel(elided_name)
        self._name_label.setObjectName("ProjectCardName")
        self._name_label.setToolTip(display_name)
        header_layout.addWidget(self._name_label, 1)
        layout.addLayout(header_layout)

        self._details_container = QWidget()
        self._details_container.setObjectName("ProjectCardDetails")
        details_layout = QVBoxLayout(self._details_container)
        details_layout.setContentsMargins(24, 6, 0, 0)
        details_layout.setSpacing(2)

        self._saved_label = QLabel("Saved: —")
        self._saved_label.setObjectName("ProjectCardDetail")
        self._shape_label = QLabel("Shape: —")
        self._shape_label.setObjectName("ProjectCardDetail")
        self._size_label = QLabel("Size: —")
        self._size_label.setObjectName("ProjectCardDetail")

        self._path_label = QLabel()
        self._path_label.setObjectName("ProjectCardPath")
        elided_path = QFontMetrics(self.font()).elidedText(
            str(file_path.absolute()), Qt.TextElideMode.ElideMiddle, width - 36
        )
        self._path_label.setText(elided_path)

        details_layout.addWidget(self._saved_label)
        details_layout.addWidget(self._shape_label)
        details_layout.addWidget(self._size_label)
        details_layout.addWidget(self._path_label)

        layout.addWidget(self._details_container)
        layout.addStretch()

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _get_card_height(self) -> int:
        return self._card_height

    def _set_card_height(self, value: int) -> None:
        self._card_height = value
        self.setFixedHeight(value)

    cardHeight = pyqtProperty(int, _get_card_height, _set_card_height)

    def _animate_to(self, target_height: int, target_opacity: float) -> None:
        self._animation_group.stop()
        self._height_animation.setStartValue(self._card_height)
        self._height_animation.setEndValue(target_height)
        self._opacity_animation.setStartValue(self._opacity_effect.opacity())
        self._opacity_animation.setEndValue(target_opacity)
        self._animation_group.start()

    def _update_expansion_state(self) -> None:
        expand = self._hovered or self._focused
        target_height = self.EXPANDED_HEIGHT if expand else self.COLLAPSED_HEIGHT
        target_opacity = 1.0 if expand else 0.0

        self._animate_to(target_height, target_opacity)

        state = "hovered" if expand else "normal"
        if self.property("cardState") != state:
            self.setProperty("cardState", state)
            self.style().unpolish(self)
            self.style().polish(self)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovered = True
        self._update_expansion_state()
        self._ensure_metadata_loaded()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovered = False
        self._update_expansion_state()
        super().leaveEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self._focused = True
        self._update_expansion_state()
        self._ensure_metadata_loaded()
        super().focusInEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.openRequested.emit(self.file_path)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.openRequested.emit(self.file_path)
        else:
            super().keyPressEvent(event)

    def _ensure_metadata_loaded(self) -> None:
        if self._metadata_requested:
            return
        self._metadata_requested = True

        try:
            stat_result = Path(self.file_path).stat()
            self._saved_label.setText(f"Saved: {format_saved_timestamp(stat_result.st_mtime)}")
            self._size_label.setText(f"Size: {format_file_size(stat_result.st_size)}")
        except OSError:
            self._saved_label.setText("Saved: unavailable")
            self._size_label.setText("Size: unavailable")

        self._shape_label.setText("Shape: loading...")
        worker = ProjectMetadataWorker(self.file_path)
        worker.signals.finished.connect(self._on_metadata_ready)
        QThreadPool.globalInstance().start(worker)

    def _on_metadata_ready(self, file_path: str, metadata: ProjectFileMetadata) -> None:
        if file_path != self.file_path:
            return

        self._metadata = metadata

        if metadata.error or metadata.row_count is None or metadata.column_count is None:
            self._shape_label.setText("Shape: unavailable")
        else:
            self._shape_label.setText(f"Shape: {metadata.row_count} rows || {metadata.column_count} columns")

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)

        open_action = menu.addAction("Open Project")
        open_action.triggered.connect(lambda: self.openRequested.emit(self.file_path))

        rename_action = menu.addAction("Rename Project")
        rename_action.triggered.connect(lambda: self.renameRequested.emit(self.file_path))

        reveal_action = menu.addAction("Show in File Explorer")
        reveal_action.triggered.connect(lambda: self.revealRequested.emit(self.file_path))

        menu.addSeparator()

        remove_action = menu.addAction("Remove from Recents")
        remove_action.triggered.connect(lambda: self.removeRequested.emit(self.file_path))

        delete_action = menu.addAction("Delete Project")
        delete_action.setIcon(IconBuilder.build(IconType.DeleteItem))
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.file_path))

        menu.exec(self.mapToGlobal(pos))
