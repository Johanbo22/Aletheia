"""
Memory-efficient diff-based history system for DataFrame operations.

This module implements a copy-on-write (CoW) strategy with operation logging
to avoid storing full DataFrame copies for each history state.
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Callable, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import uuid

class OperationType(str, Enum):
    """Types of operations that can be tracked."""
    FILTER = "filter"
    DROP_COLUMN = "drop_column"
    RENAME_COLUMN = "rename_column"
    ADD_COLUMN = "add_column"
    MODIFY_COLUMN = "modify_column"
    SORT = "sort"
    DROP_ROWS = "drop_rows"
    FILL_MISSING = "fill_missing"
    DROP_DUPLICATES = "drop_duplicates"
    CHANGE_DTYPE = "change_dtype"
    TEXT_OPERATION = "text_operation"
    SPLIT_COLUMN = "split_column"
    AGGREGATE = "aggregate"
    CUSTOM = "custom"


@dataclass
class ColumnDiff:
    """Represents changes to a single column."""
    column_name: str
    operation: str
    old_data_ref: Optional[str] = None  # Reference to old buffer
    new_data_ref: Optional[str] = None  # Reference to new buffer
    mask: Optional[np.ndarray] = None   # Boolean mask for partial changes
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffRecord:
    """A complete diff record for a single operation."""
    operation_type: OperationType
    timestamp: float
    description: str
    column_diffs: List[ColumnDiff] = field(default_factory=list)
    row_mask: Optional[np.ndarray] = None  # For row-level operations
    dropped_columns: List[str] = field(default_factory=list)
    added_columns: List[str] = field(default_factory=list)
    renamed_columns: Dict[str, str] = field(default_factory=dict)  # old -> new
    metadata: Dict[str, Any] = field(default_factory=dict)
    inverse_params: Dict[str, Any] = field(default_factory=dict)  # For undo


@dataclass
class BufferRef:
    """Reference-counted buffer for memory management."""
    buffer_id: str
    data: np.ndarray
    ref_count: int = 1
    size_bytes: int = 0

    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = self.data.nbytes

class BufferManager:
    """
    Manages shared data buffers with reference counting
    Implements a CoW system to minimize memory usage
    """
    def __init__(self) -> None:
        self._buffers: Dict[str, BufferRef] = {}
        self._total_memory_bytes: int = 0
    
    def register_buffer(self, data: np.ndarray, buffer_id: Optional[str] = None) -> str:
        """Register a new buffer and return its ID"""
        if buffer_id is None:
            import time
            hash_input = f"{time.time()}{id(data)}{data.shape}"
            buffer_id = hashlib.md5(hash_input.encode()).hexdigest()[:16]
        
        if buffer_id in self._buffers:
            self._buffers[buffer_id].ref_count += 1
        else:
            buffer_ref = BufferRef(
                buffer_id=buffer_id,
                data=data,
                ref_count=1,
                size_bytes=data.nbytes
            )
            self._buffers[buffer_id] = buffer_ref
            self._total_memory_bytes += data.nbytes
        
        return buffer_id
    
    def acquire(self, buffer_id: str) -> np.ndarray:
        """Acquire the reference to an exsisting buffer"""
        if buffer_id not in self._buffers:
            raise KeyError(f"Buffer {buffer_id} not found")
        
        self._buffers[buffer_id].ref_count += 1
        return self._buffers[buffer_id].data.copy()
    
    def release(self, buffer_id: str) -> None:
        """Release a reference to a buffer"""
        if buffer_id not in self._buffers:
            return
        
        buffer_ref = self._buffers[buffer_id]
        buffer_ref.ref_count -= 1
        
        if buffer_ref.ref_count <= 0:
            self._total_memory_bytes -= buffer_ref.size_bytes
            del self._buffers[buffer_id]
    
    def get_buffer(self, buffer_id: str) -> Optional[np.ndarray]:
        """Get the buffer data without modifying reference count"""
        if buffer_id in self._buffers:
            return self._buffers[buffer_id].data
        return None
    
    @property
    def total_memory_bytes(self) -> int:
        """Total memory in bytes used by all buffers"""
        return self._total_memory_bytes
    
    def cleanup(self) -> None:
        """Clear all buffers"""
        self._buffers.clear()
        self._total_memory_bytes = 0

@dataclass
class HistoryNode:
    """Represents a discrete state in the transformation tree"""
    node_id: str
    parent_id: Optional[str]
    diff_record: Optional[DiffRecord] = None
    children_ids: List[str] = field(default_factory=list)
    sort_state: Optional[Tuple[str, bool]] = None
    created_at: float = field(default_factory=lambda: __import__("time").time())
    
class DiffHistoryManager:
    """
    A memory-efficient history manager using a branching tree system.
    1. Stores states as nodes in a Directed Acyclic Graph (DAG)
    2. Uses Lowest Common Ancestor (LCA) algorithms for branch hopping
    """
    
    def __init__(self, max_history_memory_bytes: int = 1024 * 1024 * 1024):
        self.buffer_manager = BufferManager()
        self.max_history_memory_bytes = max_history_memory_bytes
        self.current_memory_bytes = 0
        
        self.root_id = str(uuid.uuid4())
        self.nodes: Dict[str, HistoryNode] = {self.root_id: HistoryNode(node_id=self.root_id, parent_id=None)}
        self.current_node_id = self.root_id

        # Operation log for macro export
        self.operation_log: List[Dict[str, Any]] = []
        self.sort_state: Optional[Tuple[str, bool]] = None

        # Callback for memory updates
        self.memory_update_callback: Optional[Callable[[int, int], None]] = None

        # Track base DataFrame reference
        self._base_df_ref: Optional[str] = None
        self._current_columns: List[str] = []
    
    def _compute_dataframe_memory(self, df: pd.DataFrame) -> int:
        """Calculate approximate memory footprint of a DataFrame."""
        if df is None or df.empty:
            return 0
        return df.memory_usage(deep=False).sum()

    def _notify_memory_usage(self) -> None:
        """Fire memory update callback if registered."""
        if self.memory_update_callback:
            self.memory_update_callback(
                self.current_memory_bytes + self.buffer_manager.total_memory_bytes,
                self.max_history_memory_bytes
            )
    
    def _enforce_memory_limits(self) -> None:
        """Drop oldest history states to stay within memory limits."""
        while (self.current_memory_bytes + self.buffer_manager.total_memory_bytes) > self.max_history_memory_bytes:
            leaf_nodes = [
                node for node in self.nodes.values()
                if not node.children_ids and node.node_id != self.current_node_id
            ]

            if leaf_nodes:
                leaf_nodes.sort(key=lambda n: n.created_at)
                target = leaf_nodes[0]

                freed_memory = 0
                if target.diff_record:
                    freed_memory = self._free_diff_records([target.diff_record])

                self.current_memory_bytes -= freed_memory

                if target.parent_id and target.parent_id in self.nodes:
                    self.nodes[target.parent_id].children_ids.remove(target.node_id)
                del self.nodes[target.node_id]

                print(
                    f"DEBUG: Dropped inactive leaf node {target.node_id}, freed {freed_memory / (1024 * 1024):.2f} MB")
                continue

            root_node = self.nodes.get(self.root_id)
            if root_node and len(root_node.children_ids) == 1 and root_node.node_id != self.current_node_id:
                child_id = root_node.children_ids[0]
                child_node = self.nodes[child_id]

                freed_memory = 0
                if child_node.diff_record:
                    freed_memory = self._free_diff_records([child_node.diff_record])

                self.current_memory_bytes -= freed_memory

                child_node.parent_id = None
                child_node.diff_record = None
                del self.nodes[self.root_id]
                self.root_id = child_id

                print(f"DEBUG: Pruned root node, shifted root forward, freed {freed_memory / (1024 * 1024):.2f} MB")
                continue

            print("DEBUG: Memory limit exceeded, but no safe nodes left to prune.")
            break

        self._notify_memory_usage()
    
    def _free_diff_records(self, records: List[DiffRecord]) -> int:
        """Release buffer references from diff records."""
        freed = 0
        for record in records:
            for col_diff in record.column_diffs:
                if col_diff.old_data_ref:
                    self.buffer_manager.release(col_diff.old_data_ref)
                if col_diff.new_data_ref:
                    self.buffer_manager.release(col_diff.new_data_ref)
        return freed
    
    def _create_diff_from_operation(self, old_df: pd.DataFrame, new_df: pd.DataFrame, operation_type: OperationType, params: Dict[str, Any]) -> DiffRecord:
        """Create a diff record by comparing old and new DataFrames."""
        import time
        record = DiffRecord(
            operation_type=operation_type,
            timestamp=time.time(),
            description=f"{operation_type.value} operation",
            metadata=params.copy()
        )

        record.metadata['old_index'] = old_df.index.copy(deep=True)
        record.metadata['new_index'] = new_df.index.copy(deep=True)

        old_cols = set(old_df.columns)
        new_cols = set(new_df.columns)

        dropped = old_cols - new_cols
        record.dropped_columns = list(dropped)
        for col in dropped:
            buffer_id = self.buffer_manager.register_buffer(old_df[col].values.copy())
            col_diff = ColumnDiff(
                column_name=col,
                operation="drop",
                old_data_ref=buffer_id,
                metadata={"dtype": str(old_df[col].dtype)}
            )
            record.column_diffs.append(col_diff)

        added = new_cols - old_cols
        record.added_columns = list(added)
        for col in added:
            buffer_id = self.buffer_manager.register_buffer(new_df[col].values.copy())
            col_diff = ColumnDiff(
                column_name=col,
                operation="add",
                new_data_ref=buffer_id,
                metadata={"dtype": str(new_df[col].dtype)}
            )
            record.column_diffs.append(col_diff)

        common_cols = old_cols & new_cols
        indices_identical = old_df.index.equals(new_df.index)

        for col in common_cols:
            if not old_df[col].equals(new_df[col]):
                old_ref = self.buffer_manager.register_buffer(old_df[col].values.copy())
                new_ref = self.buffer_manager.register_buffer(new_df[col].values.copy())

                mask = None
                if indices_identical:
                    try:
                        s1 = old_df[col]
                        s2 = new_df[col]
                        mask = (s1.values != s2.values) & ~(s1.isna().values & s2.isna().values)
                    except (TypeError, ValueError):
                        mask = np.ones(len(old_df), dtype=bool)

                col_diff = ColumnDiff(
                    column_name=col,
                    operation="modify",
                    old_data_ref=old_ref,
                    new_data_ref=new_ref,
                    mask=mask,
                    metadata={"dtype": str(new_df[col].dtype)}
                )
                record.column_diffs.append(col_diff)

        record.inverse_params = self._compute_inverse_params(operation_type, params, old_df, new_df)

        return record
    
    def _compute_inverse_params(self, operation_type: OperationType, params: Dict[str, Any], old_df: pd.DataFrame, new_df: pd.DataFrame) -> Dict[str, Any]:
        """Compute parameters needed to reverse an operation."""
        inverse = {"original_operation": operation_type.value}

        if operation_type == OperationType.DROP_COLUMN:
            inverse["columns_to_restore"] = params.get("columns", [])
        elif operation_type == OperationType.FILTER:
            inverse["dropped_indices"] = list(set(old_df.index) - set(new_df.index))
        elif operation_type == OperationType.SORT:
            inverse["previous_sort_state"] = self.sort_state
        elif operation_type == OperationType.RENAME_COLUMN:
            inverse["original_names"] = {v: k for k, v in params.get("renames", {}).items()}

        return inverse
    
    def save_state(self, old_df: pd.DataFrame, new_df: pd.DataFrame, operation_type: Union[OperationType, str], params: Dict[str, Any], operation_log_entry: Optional[Dict[str, Any]] = None) -> str:
        """Save a state transition as a new node, branching if necessary. Returns the new node_id."""
        if isinstance(operation_type, str):
            operation_type = OperationType(operation_type)

        diff_record = self._create_diff_from_operation(old_df, new_df, operation_type, params)

        state_memory = sum(col_diff.metadata.get("size", 0) for col_diff in diff_record.column_diffs)
        if state_memory == 0:
            state_memory = self._compute_dataframe_memory(new_df) // 10

        new_node_id = str(uuid.uuid4())
        new_node = HistoryNode(
            node_id=new_node_id,
            parent_id=self.current_node_id,
            diff_record=diff_record,
            sort_state=self.sort_state
        )

        self.nodes[self.current_node_id].children_ids.append(new_node_id)
        self.nodes[new_node_id] = new_node
        self.current_node_id = new_node_id
        self.current_memory_bytes += state_memory

        if operation_log_entry:
            self.operation_log.append(operation_log_entry)

        self._enforce_memory_limits()

        print(f"DEBUG: Branching State Saved. Total Nodes: {len(self.nodes)}, Memory: {self.current_memory_bytes / (1024*1024):.2f} MB")
        return new_node_id

    def checkout(self, current_df: pd.DataFrame, target_node_id: str) -> Tuple[Optional[pd.DataFrame], bool]:
        """Navigate to any node in the tree using LCA algorithm"""
        if target_node_id not in self.nodes:
            return None, False

        if target_node_id == self.current_node_id:
            return current_df, True

        current_path = []
        curr = self.current_node_id
        while curr:
            current_path.append(curr)
            curr = self.nodes[curr].parent_id

        target_path = []
        curr = target_node_id
        while curr:
            target_path.append(curr)
            curr = self.nodes[curr].parent_id

        lca_id = None
        for node_id in current_path:
            if node_id in target_path:
                lca_id = node_id
                break

        if not lca_id:
            return None, False

        df = current_df.copy() if current_df is not None else pd.DataFrame()

        curr = self.current_node_id
        while curr != lca_id:
            node = self.nodes[curr]
            if node.diff_record:
                df = self._apply_inverse_diff(df, node.diff_record)
            curr = node.parent_id

        redo_path = target_path[:target_path.index(lca_id)][::-1]
        for node_id in redo_path:
            node = self.nodes[node_id]
            if node.diff_record:
                df = self._apply_forward_diff(df, node.diff_record)

        self.current_node_id = target_node_id
        self.sort_state = self.nodes[target_node_id].sort_state

        return df, True
    
    def undo(self, current_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], bool]:
        """Wrapper to checkout parent node"""
        parent_id = self.nodes[self.current_node_id].parent_id
        if not parent_id:
            return None, False
        return self.checkout(current_df, parent_id)
    
    def redo(self, current_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], bool]:
        """Wrapper to checkout the most recently created child node"""
        children = self.nodes[self.current_node_id].children_ids
        if not children:
            return None, False
        return self.checkout(current_df, children[-1])
    
    def _apply_forward_diff(self, current_df: pd.DataFrame, diff_record: DiffRecord) -> pd.DataFrame:
        """Apply forward diff to reconstruct the state after an operation."""
        new_index = diff_record.metadata.get('new_index')
        df = current_df.copy() if current_df is not None else pd.DataFrame()

        # Reshape array layout to map to the forward state
        if new_index is not None and not df.index.equals(new_index):
            df = df.reindex(new_index)

        # Remove dropped columns
        for col_name in diff_record.dropped_columns:
            if col_name in df.columns:
                df = df.drop(columns=[col_name])

        # Add added columns
        for col_diff in diff_record.column_diffs:
            if col_diff.operation == "add":
                new_data = self.buffer_manager.get_buffer(col_diff.new_data_ref)
                if new_data is not None:
                    df[col_diff.column_name] = new_data

        # Apply modified columns
        for col_diff in diff_record.column_diffs:
            if col_diff.operation == "modify":
                new_data = self.buffer_manager.get_buffer(col_diff.new_data_ref)
                if new_data is not None and col_diff.column_name in df.columns:
                    if col_diff.mask is not None and len(new_data) == len(df):
                        current_vals = df[col_diff.column_name].values
                        df[col_diff.column_name] = np.where(col_diff.mask, new_data, current_vals)
                    else:
                        df[col_diff.column_name] = new_data

        # Handle renamed columns
        for old_name, new_name in diff_record.renamed_columns.items():
            if old_name in df.columns and new_name not in df.columns:
                df = df.rename(columns={old_name: new_name})

        return df

    def _apply_inverse_diff(self, current_df: pd.DataFrame, diff_record: DiffRecord) -> pd.DataFrame:
        """Apply inverse of a diff record to reconstruct previous state."""
        old_index = diff_record.metadata.get('old_index')
        df = current_df.copy()

        # Reshape array layout returning all pruned rows into place using NaN placeholders
        if old_index is not None and not df.index.equals(old_index):
            df = df.reindex(old_index)

        # Restore dropped columns
        for col_diff in diff_record.column_diffs:
            if col_diff.operation == "drop":
                old_data = self.buffer_manager.get_buffer(col_diff.old_data_ref)
                if old_data is not None:
                    df[col_diff.column_name] = old_data

        # Remove added columns
        for col_name in diff_record.added_columns:
            if col_name in df.columns:
                df = df.drop(columns=[col_name])

        # Restore modified columns
        for col_diff in diff_record.column_diffs:
            if col_diff.operation == "modify":
                old_data = self.buffer_manager.get_buffer(col_diff.old_data_ref)
                if old_data is not None and col_diff.column_name in df.columns:
                    if col_diff.mask is not None and len(old_data) == len(df):
                        current_vals = df[col_diff.column_name].values
                        df[col_diff.column_name] = np.where(col_diff.mask, old_data, current_vals)
                    else:
                        df[col_diff.column_name] = old_data

        return df
    
    def can_undo(self) -> bool:
        if not hasattr(self, 'nodes') or not hasattr(self, 'current_node_id'): return False
        return self.nodes[self.current_node_id].parent_id is not None

    def can_redo(self) -> bool:
        if not hasattr(self, 'nodes') or not hasattr(self, 'current_node_id'): return False
        return len(self.nodes[self.current_node_id].children_ids) > 0

    def clear(self) -> None:
        """Clear all history and free all buffers."""
        self.root_id = str(uuid.uuid4())
        self.nodes = {self.root_id: HistoryNode(node_id=self.root_id, parent_id=None)}
        self.current_node_id = self.root_id

        self.operation_log.clear()
        self.sort_state = None
        self.current_memory_bytes = 0
        self.buffer_manager.cleanup()
        self._notify_memory_usage()

    def get_history_info(self) -> Dict[str, Any]:
        """Get information about history state using tree traversal."""
        path_to_root = []
        curr = self.current_node_id
        while curr and curr != self.root_id:
            path_to_root.append(curr)
            curr = self.nodes[curr].parent_id

        return {
            "history": self.operation_log.copy(),
            "current_node_id": self.current_node_id,
            "root_id": self.root_id,
            "nodes": self.nodes,
            "undo_count": len(path_to_root),
            "redo_count": len(self.nodes[self.current_node_id].children_ids),
            "memory_bytes": self.current_memory_bytes + self.buffer_manager.total_memory_bytes
        }

    def export_pipeline_macro(self, filepath: Union[str, Path]) -> None:
        """Export operation log to JSON file."""
        active_log = self.operation_log[:len(self.undo_stack)]
        if not active_log:
            raise ValueError("No operations to export")

        target_path = Path(filepath)
        with target_path.open("w", encoding="utf-8") as f:
            json.dump(active_log, f, indent=4)

    def load_pipeline_macro(
        self,
        macro_source: Union[str, Path, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Load operations from JSON file or list."""
        if isinstance(macro_source, (str, Path)):
            source_path = Path(macro_source)
            with source_path.open("r", encoding="utf-8") as f:
                operations = json.load(f)
        elif isinstance(macro_source, list):
            operations = macro_source
        else:
            raise ValueError("macro_source must be filepath or list")

        if not isinstance(operations, list):
            raise ValueError("Invalid format: expected list of operations")

        return operations