from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint

from core.data_handler import DataHandler
from ui.widgets.ControlElements import DataPlotStudioLineEdit
from ui.widgets import DataPlotStudioButton
from ui.icons import IconBuilder, IconType
from ui.workers import SearchWorker

class DataSearchBar(QWidget):
    """
    The inline search functionality widget for the data table
    Handles UI, search timer, and threads
    """
    match_found = pyqtSignal(int, int)
    close_requested = pyqtSignal()
    clear_selection_requested = pyqtSignal()

    def __init__(self, data_handler: DataHandler, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data_handler = data_handler

        self.current_search_matches: list[tuple[int, int]] = []
        self.current_search_index: int = -1
        self.search_worker: SearchWorker | None = None
        self.search_token: int = 0
        self.last_searched_text: str = ""

        self.search_timer = QTimer(self)
        search_timer_ms = 300
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(search_timer_ms)
        self.search_timer.timeout.connect(self._execute_search_worker)

        # Animation for when the search bar is requested
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        animation_duration: int = 200
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(animation_duration)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(animation_duration)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("InlineSearchBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        search_layout = QHBoxLayout(self)
        search_layout.setContentsMargins(5, 5, 5, 5)

        search_icon = QLabel()
        search_icon.setPixmap(IconBuilder.build(IconType.Search).pixmap(16, 16))
        search_layout.addWidget(search_icon)

        self.search_input = DataPlotStudioLineEdit(parent=self)
        self.search_input.setPlaceholderText("Find in table (Enter for next)...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self.search_next)
        search_layout.addWidget(self.search_input)

        self.search_count_label = QLabel("0/0 matches")
        self.search_count_label.setFixedWidth(100)
        self.search_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.search_count_label.setProperty("styleClass", "muted_text")
        search_layout.addWidget(self.search_count_label)

        self.search_prev_btn = DataPlotStudioButton("", parent=self, padding="4px")
        self.search_prev_btn.setIcon(IconBuilder.build(IconType.UpArrow))
        self.search_prev_btn.setToolTip("Previous Match")
        self.search_prev_btn.clicked.connect(self.search_prev)
        search_layout.addWidget(self.search_prev_btn)

        self.search_next_btn = DataPlotStudioButton("", parent=self, padding="4px")
        self.search_next_btn.setIcon(IconBuilder.build(IconType.DownArrow))
        self.search_next_btn.setToolTip("Next Match (Enter)")
        self.search_next_btn.clicked.connect(self.search_next)
        search_layout.addWidget(self.search_next_btn)

        self.search_close_btn = DataPlotStudioButton("", parent=self, padding="4px")
        self.search_close_btn.setIcon(IconBuilder.build(IconType.Close))
        self.search_close_btn.setToolTip("Close Search (Esc)")
        self.search_close_btn.clicked.connect(self.close_search)
        search_layout.addWidget(self.search_close_btn)

        search_layout.addStretch()
        self.setVisible(False)

    def open_search(self) -> None:
        """
        Displays the search bar with a slide down animation and focus the input
        """
        self.setVisible(True)

        current_pos: QPoint = self.pos()
        start_pos: QPoint = QPoint(current_pos.x(), current_pos.y() - 50)
        self.move(start_pos)

        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)

        self.slide_animation.stop()
        self.slide_animation.setStartValue(start_pos)
        self.slide_animation.setEndValue(current_pos)

        self.opacity_animation.start()
        self.slide_animation.start()

        self.search_input.setFocus()
        self.search_input.selectAll()

    def close_search(self) -> None:
        """
        Hides the search bar with a slide up animation, clears inputs and requests selection clear
        """
        current_pos: QPoint = self.pos()
        end_pos = QPoint(current_pos.x(), current_pos.y() - 50)

        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)

        self.slide_animation.stop()
        self.slide_animation.setStartValue(current_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.finished.connect(self._on_close_animation_finished)

        self.opacity_animation.start()
        self.slide_animation.start()

    def _on_close_animation_finished(self) -> None:
        """Called when the close animation finishes to hide the widget"""
        self.slide_animation.finished.disconnect(self._on_close_animation_finished)
        self.hide()
        self.search_input.clear()
        self.clear_selection_requested.emit()

    def _on_search_text_changed(self, text: str) -> None:
        self.pending_search_text = text
        self.search_count_label.setText("...")
        self.search_timer.start()

    def _execute_search_worker(self) -> None:
        text = self.pending_search_text

        if self.last_searched_text == text:
            if self.search_worker is not None and self.search_worker.isRunning():
                return
        self.last_searched_text = text

        self.search_token += 1
        current_token = self.search_token

        if not text or self.data_handler.df is None or self.data_handler.df.empty:
            self._handle_search_results([], current_token)
            return

        self.search_worker = SearchWorker(self.data_handler.df, text, current_token, parent=self)
        self.search_worker.finished_search.connect(self._handle_search_results)
        self.search_worker.start()

    def _handle_search_results(self, matches: list[tuple[int, int]], token: int) -> None:
        if token != self.search_token:
            return

        self.current_search_matches = matches
        self.current_search_index = -1

        if self.current_search_matches:
            self.current_search_index = 0
            self._highlight_current_match()
        else:
            self.search_count_label.setText("0/0 matches")
            self.clear_selection_requested.emit()

    def search_next(self) -> None:
        """Advance to the next search match"""
        if not self.current_search_matches:
            return
        self.current_search_index = (self.current_search_index + 1) % len(self.current_search_matches)
        self._highlight_current_match()

    def search_prev(self) -> None:
        """Go to the previous search match"""
        if not self.current_search_matches:
            return
        self.current_search_index = (self.current_search_index - 1) % len(self.current_search_matches)

    def _highlight_current_match(self) -> None:
        if 0 <= self.current_search_index < len(self.current_search_matches):
            row, col = self.current_search_matches[self.current_search_index]
            self.match_found.emit(row, col)

            total = len(self.current_search_matches)
            current = self.current_search_index + 1
            self.search_count_label.setText(f"{current}/{total} matches")
            self.search_input.setFocus()