import logging
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import CursorResult, Row

logger: logging.Logger = logging.getLogger(__name__)

PREVIEW_ROW_LIMIT: int = 5
MAX_CELL_DISPLAY_LENGTH: int = 200
MAX_CELL_TOOLTIP_LENGTH: int = 1000
SQL_NULL_DISPLAY: str = "NULL"
POSTRESQL_DIALECT_NAME: str = "postgresql"

SQL_COMMENT_PATTERN: re.Pattern[str] = re.compile(r"(--[^\n]*|/\*.*?\*/)", flags=re.S)
SQL_LITERAL_PATTERN: re.Pattern[str] = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", flags=re.S)
TRAILING_SEMICOLON_PATTERN: re.Pattern[str] = re.compile(r";+\s*$")
FORBIDDEN_SQL_KEYWORD_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|ATTACH|DETACH|PRAGMA|CALL|EXEC|EXECUTE|COPY)\b",
    re.IGNORECASE,
)

@dataclass(frozen=True)
class QueryPreviewRequest:
    """
    Immutable configuration to execute a bounded database query

    :param connection_string: SQLAlchemy-compatible database connection URI.
    :param query: Read-only SQL query string entered by the user.
    :param row_limit: Maximum number of records to return for validation.
    :param source_label: Optional label describing the preview target (e.g., table name).
    """
    connection_string: str
    query: str
    row_limit: int = PREVIEW_ROW_LIMIT
    source_label: str = ""

@dataclass(frozen=True)
class QueryPreviewResult:
    """
    Immutable result container holding formatted preview records and column metadata.
    :param columns: Ordered column header names returned by the SQL cursor.
    :param rows: Formatted display text per row and column, capped at ``row_limit``.
    :param tooltips: Full or lightly truncated cell strings for hover inspection.
    :param null_mask: Boolean flags indicating SQL NULL / NaN cells per row and column.
    :param numeric_columns: Boolean flags indicating columns whose non-null values are numeric.
    :param has_more_rows: True when the query produces more rows than ``row_limit``.
    :param source_label: Optional label describing the preview target.
    """

    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    tooltips: tuple[tuple[str, ...], ...]
    null_mask: tuple[tuple[bool, ...], ...]
    numeric_columns: tuple[bool, ...]
    has_more_rows: bool
    source_label: str = ""

def strip_trailing_semicolons(query: str) -> str:
    """
    Remove trailing whitespace and terminating semicolons from a SQL query

    :param query: Raw SQL query
    :return: Trimmed SQL query without trailing semicolons
    """
    return TRAILING_SEMICOLON_PATTERN.sub("", query.strip()).strip()

def is_valid_readonly_query(query: str) -> bool:
    """
    Verify that a SQL string represents a single read-only data retrieval statement.

    Comments and quoted literals are neutralised before checking statement boundaries
    so multi-statement payloads and mutating DDL/DML commands are rejected before execution.

    :param query: Raw SQL text from the query editor.
    :return: True if the query is a single read-only SELECT, WITH, TABLE, VALUES, or FROM query.
    """
    without_comments: str = SQL_COMMENT_PATTERN.sub(" ", query).strip()
    without_semicolons: str = strip_trailing_semicolons(without_comments)
    if not without_semicolons:
        return False

    neutralised_literals: str = SQL_LITERAL_PATTERN.sub("'literal'", without_semicolons)
    if ";" in neutralised_literals:
        return False

    if FORBIDDEN_SQL_KEYWORD_PATTERN.match(without_semicolons):
        return False

    lowered_query: str = without_semicolons.lower()
    if lowered_query.startswith("select"):
        return bool(re.match(r"^select\s+\S+", without_semicolons, re.IGNORECASE))
    if lowered_query.startswith("with"):
        return bool(re.search(r"\b(select|values|table)\b", without_semicolons, re.IGNORECASE))
    if lowered_query.startswith(("table ", "values ", "values(", "from ")):
        return True

    return False

def _truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}…"

def _format_row_cell(row: Row, col_idx: int) -> tuple[str, str, bool, bool]:
    """Extract display string, tooltip string, null flag, and numeric flag for one cell."""
    raw_value = row[col_idx]
    if raw_value is None:
        return SQL_NULL_DISPLAY, SQL_NULL_DISPLAY, True, False

    if isinstance(raw_value, float) and math.isnan(raw_value):
        return SQL_NULL_DISPLAY, SQL_NULL_DISPLAY, True, False

    if isinstance(raw_value, Decimal) and raw_value.is_nan():
        return SQL_NULL_DISPLAY, SQL_NULL_DISPLAY, True, False

    if type(raw_value).__name__ == "NaTType":
        return SQL_NULL_DISPLAY, SQL_NULL_DISPLAY, True, False

    if isinstance(raw_value, (bytes, bytearray, memoryview)):
        blob_summary: str = f"<BLOB ({len(raw_value)} B)"
        return blob_summary, blob_summary, False, False

    is_numeric: bool = isinstance(raw_value, (int, float, Decimal)) and not isinstance(raw_value, bool)
    full_text: str = str(raw_value)
    display_text: str = _truncate_text(full_text, MAX_CELL_DISPLAY_LENGTH)
    tooltip_text: str = _truncate_text(full_text, MAX_CELL_TOOLTIP_LENGTH)
    return display_text, tooltip_text, False, is_numeric

def _build_preview_matrix(
        limited_rows: Sequence[Row],
        column_count: int
) -> tuple[
    tuple[tuple[str, ...], ...],
    tuple[tuple[str, ...], ...],
    tuple[tuple[bool, ...], ...],
    tuple[bool, ...],
]:
    """Convert bounded SQLAlchemy rows into immutable string, tooltip, null, and numeric tuples."""
    formatted_rows: list[tuple[str, ...]] = []
    tooltip_rows: list[tuple[str, ...]] = []
    null_rows: list[tuple[bool, ...]] = []
    all_numeric: list[bool] = [True] * column_count
    seen_non_null: list[bool] = [False] * column_count

    for row in limited_rows:
        row_cells: list[str] = []
        row_tooltips: list[str] = []
        row_nulls: list[bool] = []
        for col_idx in range(column_count):
            display_val, tooltip_val, is_null, is_numeric = _format_row_cell(row, col_idx)
            row_cells.append(display_val)
            row_tooltips.append(tooltip_val)
            row_nulls.append(is_null)
            if not is_null:
                seen_non_null[col_idx] = True
                if not is_numeric:
                    all_numeric[col_idx] = False

        formatted_rows.append(tuple(row_cells))
        tooltip_rows.append(tuple(row_tooltips))
        null_rows.append(tuple(row_nulls))

    numeric_columns: tuple[bool, ...] = tuple(
        seen_non_null[idx] and all_numeric[idx] for idx in range(column_count)
    )
    return (
        tuple(formatted_rows),
        tuple(tooltip_rows),
        tuple(null_rows),
        numeric_columns
    )

def execute_query_preview(request: QueryPreviewRequest) -> QueryPreviewResult:
    """
    Execute a read-only SQL query and return at most ``request.row_limit`` records.

    Fetches ``row_limit + 1`` rows so ``has_more_rows`` can be reported accurately
    without running an extra ``COUNT(*)`` query, and exits the connection block
    without committing so accidental side effects are rolled back.

    :param request: Validated preview execution parameters.
    :return: Immutable :class:`QueryPreviewResult` containing columns and up to ``row_limit`` rows.
    :raises ValueError: If the connection string, row limit, or read-only query validation fails.
    """
    if not request.connection_string.strip():
        raise ValueError("A valid database connection is required to preview a query")
    if request.row_limit < 1:
        raise ValueError("Preview row limit must be at least 1")
    if not is_valid_readonly_query(request.query):
        raise ValueError("Query must be a single read-only SELECT, WITH, TABLE, or VALUES statement")

    cleaned_query: str = strip_trailing_semicolons(request.query)
    fetch_count: int = request.row_limit + 1
    engine: Engine | None = None

    try:
        engine = create_engine(request.connection_string)
        with engine.connect() as connection:
            active_connection = (
                connection.execution_options(stream_results=True, max_row_buffer=fetch_count)
                if engine.dialect.name == POSTRESQL_DIALECT_NAME
                else connection
            )
            result: CursorResult = active_connection.execute(text(cleaned_query))
            try:
                if not result.returns_rows:
                    raise ValueError("The query did not return a tabular result set")
                columns: tuple[str, ...] = tuple(str(col_name) for col_name in result.keys())
                fetched_rows: Sequence[Row] = result.fetchmany(fetch_count)
            finally:
                result.close()
            connection.rollback()
    finally:
        if engine is not None:
            engine.dispose()

    has_more_rows: bool = len(fetched_rows) > request.row_limit
    limited_rows: Sequence[Row] = fetched_rows[:request.row_limit]
    rows, tooltips, null_mask, numeric_columns = _build_preview_matrix(limited_rows, len(columns))

    return QueryPreviewResult(
        columns=columns,
        rows=rows,
        tooltips=tooltips,
        null_mask=null_mask,
        numeric_columns=numeric_columns,
        has_more_rows=has_more_rows,
        source_label=request.source_label,
    )
