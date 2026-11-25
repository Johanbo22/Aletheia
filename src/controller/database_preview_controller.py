from PyQt6.QtCore import QObject, QThreadPool

from src.core.database_query_preview import (PREVIEW_ROW_LIMIT, QueryPreviewRequest, QueryPreviewResult)
from src.core.global_signals import ToastLevel, global_signals
from src.ui.components.query_preview_panel import QueryPreviewPanel
from src.ui.workers import QueryPreviewWorker

class DatabasePreviewController(QObject):
    """
    Coordinates asynchronous SQL query preview execution for :class:`QueryPreviewPanel`.
    Uses monotonically increasing generation tokens so stale background worker
    completions are ignored when connection settings change or new previews start.
    """

    def __init__(
            self,
            preview_panel: QueryPreviewPanel,
            threadpool: QThreadPool | None = None,
            parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._preview_panel: QueryPreviewPanel = preview_panel
        resolved_pool: QThreadPool | None = threadpool or QThreadPool.globalInstance()
        if resolved_pool is None:
            resolved_pool = QThreadPool(self)
        self._threadpool: QThreadPool = resolved_pool

        self._generation: int = 0
        self._is_loading: bool = False
        self._is_query_valid: bool = False

    @property
    def is_loading(self) -> bool:
        """Return True while worker is running"""
        return self._is_loading

    def set_query_valid(self, is_valid: bool) -> None:
        """Update query validity state"""
        self._is_query_valid = is_valid
        self._preview_panel.set_can_execute(is_valid and not self._is_loading)

    def execute_preview(
            self,
            connection_string: str,
            query: str,
            source_label: str = ""
    ) -> None:
        """Starts an async worker to fetch 5 records"""
        self._generation += 1
        generation: int = self._generation
        self._is_loading = True
        self._preview_panel.set_loading_state()

        request: QueryPreviewRequest = QueryPreviewRequest(
            connection_string=connection_string,
            query=query,
            row_limit=PREVIEW_ROW_LIMIT,
            source_label=source_label
        )
        worker: QueryPreviewWorker = QueryPreviewWorker(request)
        worker.signals.finished.connect(
            lambda result, gen=generation: self._on_preview_finished(result, gen)
        )
        worker.signals.error.connect(
            lambda err_msg, gen=generation: self._on_preview_error(err_msg, gen)
        )
        self._threadpool.start(worker)

    def _on_preview_finished(self, result: QueryPreviewResult, generation: int) -> None:
        if generation != self._generation:
            return
        self._is_loading = False
        self._preview_panel.display_preview_result(result)
        self._preview_panel.set_can_execute(self._is_query_valid)

    def _on_preview_error(self, error_message: str, generation: int) -> None:
        if generation != self._generation:
            return
        self._is_loading = False
        self._preview_panel.set_error_state("Query preview execution failed")
        self._preview_panel.set_can_execute(self._is_query_valid)

        global_signals.request_toast(
            "Query Preview Error",
            f"Could not execute query preview:\n{error_message}",
            ToastLevel.ERROR
        )
        global_signals.request_log(
            f"Database query preview failed: {error_message}",
            "ERROR"
        )

    def reset(self) -> None:
        """Cancel preview callbacks and clear preview table"""
        self._generation += 1
        self._is_loading = False
        self._preview_panel.clear_preview()
        self._preview_panel.set_can_execute(self._is_query_valid)
