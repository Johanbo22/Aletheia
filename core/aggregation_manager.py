"""
Aggregation Manager is for managing saved data aggregations

Provides methods for storing, retrieving and reapplying
data aggregation configurations
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
from core.data_mutator import resolve_agg_config

@dataclass
class SavedAggregation:
    """Represents a saved aggregation configuration and its resulting dataframe."""
    name: str
    description: str
    group_by: List[str]
    agg_config: Dict[str, Union[str, List[str]]]
    date_grouping: Optional[Dict[str, str]] = None
    result_df: Optional[pd.DataFrame] = None
    created_at: datetime = field(default_factory=datetime.now)
    row_count: int = 0
    rename_mapping: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the aggregation metadata to a dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "group_by": self.group_by,
            "agg_config": self.agg_config,
            "date_grouping": self.date_grouping,
            "created_at": self.created_at.isoformat(),
            "row_count": self.row_count,
            "rename_mapping": self.rename_mapping
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedAggregation":
        """Creates a SavedAggregation instance from a dictionary, maintaining legacy compatibility."""
        created_at_str = data.get("created_at")
        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()
        
        agg_config = data.get("agg_config")
        if agg_config is None:
            cols = data.get("agg_columns", [])
            func = data.get("agg_func", "count")
            agg_config = {col: func for col in cols}

        date_grouping_data = data.get("date_grouping")

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            group_by=list(data.get("group_by", [])),
            agg_config=dict(agg_config),
            date_grouping=dict(date_grouping_data) if date_grouping_data else None,
            created_at=created_at,
            row_count=data.get("row_count", 0),
            rename_mapping=data.get("rename_mapping")
        )

class AggregationManager:
    """Manages saved data aggregations, allowing storage, retrieval, and reapplication."""

    def __init__(self) -> None:
        self.saved_aggregations: Dict[str, SavedAggregation] = {}
    
    def save_aggregation(self, name: str, description: str, group_by: List[str], agg_config: Dict[str, str], result_df: pd.DataFrame, date_grouping: Optional[Dict[str, str]] = None, rename_mapping: Optional[Dict[str, str]] = None) -> SavedAggregation:
        """Saves a new aggregation configuration and its initial result."""
        if name in self.saved_aggregations:
            raise ValueError(f"Aggregation '{name}' already exists")
        
        agg = SavedAggregation(
            name=name,
            description=description,
            group_by=list(group_by),
            agg_config=dict(agg_config),
            date_grouping=dict(date_grouping) if date_grouping else None,
            result_df=result_df.copy(),
            row_count=len(result_df),
            rename_mapping=rename_mapping
        )

        self.saved_aggregations[name] = agg
        return agg
    
    def get_aggregation(self, name: str) -> Optional[SavedAggregation]:
        """Retrieves a saved aggregation by its exact name."""
        return self.saved_aggregations.get(name)
    
    def list_aggregations(self) -> List[str]:
        """Lists all stored aggregation names."""
        return list(self.saved_aggregations.keys())
    
    def delete_aggregation(self, name: str) -> bool:
        """Deletes an aggregation. Returns True if successfully found and deleted."""
        return self.saved_aggregations.pop(name, None) is not None
    
    def get_aggregation_df(self, name: str) -> Optional[pd.DataFrame]:
        """Returns a safe copy of the resulting dataframe for a saved aggregation."""
        agg = self.saved_aggregations.get(name)
        return agg.result_df.copy() if agg and agg.result_df is not None else None
    
    def reapply_aggregation(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Reapplies an existing aggregation configuration to a new dataset."""
        agg = self.saved_aggregations.get(name)

        if not agg:
            raise ValueError(f"Aggregation '{name}' not found")
        
        if not agg.group_by:
            raise ValueError(f"Aggregation '{name}' requires at least one group_by column")
        
        # Fail if the required columns are missing in the new dataframe
        df_columns_set = set(df.columns)
        missing_group_cols = list(set(agg.group_by) - df_columns_set)
        if missing_group_cols:
            raise KeyError(f"Cannot reapply aggregation. Missing grouping columns: {missing_group_cols}")

        missing_agg_cols = list(set(agg.agg_config.keys()) - df_columns_set)
        if missing_agg_cols:
            raise KeyError(f"Cannot reapply aggregation. Missing aggregation columns: {missing_agg_cols}")

        try:
            resolved_agg_config = resolve_agg_config(agg.agg_config)
            result = df.groupby(agg.group_by, dropna=False).agg(resolved_agg_config).reset_index()

            if isinstance(result.columns, pd.MultiIndex):
                result.columns = [f"{str(col[0])}_{str(col[1])}" if len(col) > 1 and col[1] else str(col[0]) for col in
                                  result.columns]
            if agg.rename_mapping:
                result = result.rename(columns=agg.rename_mapping)
        except Exception as error:
            raise RuntimeError(f"Failed to apply Pandas aggregation: {str(error)}")
        
        # update the manager state
        agg.result_df = result.copy()
        agg.row_count = len(result)
        
        return result
    
    def export_aggregation(self) -> Dict[str, Any]:
        """Exports all aggregations to a dictionary format for project file saving."""
        return {
            name: agg.to_dict() for name, agg in self.saved_aggregations.items()
        }
    
    def import_aggregations(self, data: Dict[str, Any]) -> None:
        """Imports aggregations from a parsed dictionary project file."""
        self.saved_aggregations.clear()
        for name, agg_data in data.items():
            self.saved_aggregations[name] = SavedAggregation.from_dict(agg_data)
    
    def clear_all(self) -> None:
        """Clears all stored aggregations from memory."""
        self.saved_aggregations.clear()