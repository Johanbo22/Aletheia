# core/logger.py
"""
Logger module for Aletheia logging functionality

This modules provides the Logger class which is a singleton that handles all
logging for Aletheia.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Deque
from collections import deque, Counter
import textwrap

from resources.version import APPLICATION_NAME


class LogEntry:
    """Represents a single log entry"""
    
    def __init__(self, level: str, message: str, timestamp: Optional[datetime] = None) -> None:
        self.timestamp = timestamp or datetime.now()
        self.level = level
        self.message = message
    
    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M:%S')}] [{self.level:8s}] {self.message}"
    
    def to_detailed_str(self) -> str:
        """Return detailed log entry with full timestamp"""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] [{self.level:8s}] {self.message}"


class Logger:
    """Handles all logging for Aletheia"""

    _instance: Optional["Logger"] = None
    
    def __init__(self, max_entries: int = 1000) -> None:
        if Logger._instance is not None:
            raise RuntimeError("Use Logger.get_instance() to get the singleton instance")
        self.max_entries = max_entries
        self.entries: Deque[LogEntry] = deque(maxlen=max_entries)

    @classmethod
    def get_instance(cls, max_entries: int = 1000) -> "Logger":
        """Get the singleton logger instance"""
        if cls._instance is None:
            cls._instance = Logger(max_entries)
        return cls._instance
    
    def _add_entry(self, level: str, message: str) -> None:
        """Add log entry"""
        entry = LogEntry(level, message)
        self.entries.append(entry)
    
    def info(self, message: str) -> None:
        """Log info message"""
        self._add_entry("INFO", message)
    
    def success(self, message: str) -> None:
        """Log success message"""
        self._add_entry("SUCCESS", message)
    
    def warning(self, message: str) -> None:
        """Log warning message"""
        self._add_entry("WARNING", message)
    
    def error(self, message: str) -> None:
        """Log error message"""
        self._add_entry("ERROR", message)
    
    def data_imported(self, filename: str, rows: int, cols: int, file_size_kb: float) -> None:
        """Log data import"""
        msg = f"Data imported: {filename} ({rows:,} rows x {cols} cols, {file_size_kb:.1f} KB)"
        self.success(msg)
    
    def google_sheets_imported(self, sheet_id: str, sheet_name: str, rows: int, cols: int) -> None:
        """Log Google Sheets import"""
        msg = f"Google Sheet imported: '{sheet_name}' ({rows:,} rows × {cols} cols)"
        self.success(msg)
    
    def filter_applied(self, column: str, condition: str, value: str, rows_before: int, rows_after: int) -> None:
        """Log filter operation"""
        rows_removed = rows_before - rows_after
        msg = f"Filter applied: {column} {condition} '{value}' | Rows: {rows_before:,} → {rows_after:,} (-{rows_removed:,})"
        self.success(msg)
    
    def duplicates_removed(self, count: int) -> None:
        """Log duplicate removal"""
        msg = f"Removed {count:,} duplicate row(s)"
        self.success(msg)
    
    def missing_values_dropped(self, count: int) -> None:
        """Log missing value removal"""
        msg = f"Dropped {count:,} row(s) with missing values"
        self.success(msg)
    
    def missing_values_filled(self, count: int, method: str = "forward fill") -> None:
        """Log missing value filling"""
        msg = f"Filled {count:,} missing value(s) using {method}"
        self.success(msg)
    
    def column_dropped(self, column: str) -> None:
        """Log column drop"""
        msg = f"Column dropped: '{column}'"
        self.success(msg)
    
    def column_renamed(self, old_name: str, new_name: str) -> None:
        """Log column rename"""
        msg = f"Column renamed: '{old_name}' → '{new_name}'"
        self.success(msg)
    
    def data_aggregated(self, group_by: str, agg_col: str, agg_func: str, result_rows: int) -> None:
        """Log aggregation"""
        msg = f"Data aggregated: groupby('{group_by}').{agg_func}('{agg_col}') | Result: {result_rows:,} rows"
        self.success(msg)
    
    def data_exported(self, filename: str, format_type: str, rows: int, cols: int) -> None:
        """Log data export"""
        msg = f"Data exported: {filename} ({format_type.upper()}, {rows:,} rows × {cols} cols)"
        self.success(msg)
    
    def code_exported(self, filename: str, script_type: str) -> None:
        """Log code export"""
        msg = f"Python script exported: {filename} ({script_type})"
        self.success(msg)
    
    def plot_generated(self, plot_type: str, x_col: str, y_col: str, annotations: int = 0) -> None:
        """Log plot generation"""
        ann_text = f" with {annotations} annotation(s)" if annotations > 0 else ""
        msg = f"Plot generated: {plot_type} | X: '{x_col}', Y: '{y_col}'{ann_text}"
        self.success(msg)
    
    def plot_cleared(self) -> None:
        """Log plot clear"""
        self.info("Plot cleared")
    
    def data_reset(self) -> None:
        """Log data reset"""
        msg = "Data reset to original state"
        self.success(msg)
    
    def undo_performed(self) -> None:
        """Log undo"""
        msg = "Undo: Previous state restored"
        self.info(msg)
    
    def redo_performed(self) -> None:
        """Log redo"""
        msg = "Redo: Action restored"
        self.info(msg)
    
    def project_created(self) -> None:
        """Log new project"""
        self.success("New project created")
    
    def project_loaded(self, filename: str) -> None:
        """Log project load"""
        self.success(f"Project loaded: {filename}")
    
    def project_saved(self, filename: str) -> None:
        """Log project save"""
        self.success(f"Project saved: {filename}")

    def subset_created(self, name: str, rows: int) -> None:
        """Log subset creation"""
        message = f"Subset created: '{name}' ({rows:,} rows)"
        self.success(message)
    
    def subset_inserted(self, name: str, rows: int) -> None:
        """Log subset insertion into active """
        message = f"Subset inserted as active data: '{name}' ({rows:,} rows)"
        self.info(message)

    def subset_deleted(self, name: str) -> None:
        """Log deletion of subseet"""
        message = f"Subset deleted: '{name}'"
        self.info(message)
    
    def aggregation_saved(self, name: str) -> None:
        """Log aggregation saved"""
        message = f"Aggregation saved: '{name}'"
        self.success(message)
    
    def aggregation_deleted(self, name: str) -> None:
        """Log deletion af agg"""
        message = f"Aggregation deleted: '{name}'"
        self.info(message)
    
    def data_melted(self, id_vars: List[str], value_vars: Optional[List[str]], rows_before: int, rows_after: int) -> None:
        """Log pivot/melt """
        formatted_value_vars = str(value_vars) if value_vars else "All other columns"
        message = f"Data melted: id_vars={id_vars}, value_vars={formatted_value_vars} | Rows: {rows_before:,} -> {rows_after:,}"
        self.success(message)
    
    def column_data_type_changed(self, column: str, old_data_type: str, new_data_type: str) -> None:
        """Kig data type change of column"""
        message = f"Column type changed. '{column}' ({old_data_type} -> {new_data_type})"
        self.success(message)

    def get_all_logs(self) -> str:
        """Get all logs as formatted string"""
        return "\n".join(str(entry) for entry in self.entries)
    
    def get_detailed_logs(self) -> str:
        """Get detailed logs with full timestamps"""
        return "\n".join(entry.to_detailed_str() for entry in self.entries)
    
    def export_logs(self, filepath: str, detailed: bool = True) -> str:
        """Export logs to file"""
        path = Path(filepath)
        
        try:
            content: str = self._generate_log_report(detailed)
            
            with open(path, 'w', encoding="utf-8") as f:
                f.write(content)
            
            return str(path)
        except OSError as os_error:
            raise RuntimeError(f"Failed to export logs to {filepath}: {str(os_error)}") from os_error
    
    def _generate_log_report(self, detailed: bool = True) -> str:
        """Generate formatted log report"""
        header = textwrap.dedent(f"""
            {'='*120}
            {APPLICATION_NAME} - Session Log Report
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            This log is automatically generated
            {'='*120}

            SUMMARY
            -------
            Total Log Entries: {len(self.entries)}
            Session Duration: {self._get_session_duration()}

            LOG ENTRIES
            -----------
        """)
        log_content = self.get_detailed_logs() if detailed else self.get_all_logs()
        
        footer = textwrap.dedent(f"""\
            
            {'='*120}
            END OF LOG REPORT
            {'='*120}
        """)
        
        return header + log_content + footer
    
    def _get_session_duration(self) -> str:
        """Calculate session duration"""
        if not self.entries:
            return "0:00:00"
        
        start = self.entries[0].timestamp
        end = self.entries[-1].timestamp
        delta = end - start
        
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    
    def clear(self) -> None:
        """Clear all log entries"""
        self.entries.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics"""
        level_counts = dict(Counter(entry.level for entry in self.entries))
        
        return {
            'total_entries': len(self.entries),
            'by_level': level_counts,
            'session_duration': self._get_session_duration(),
        }