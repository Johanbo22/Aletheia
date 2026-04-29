from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd

@dataclass
class SavedAggregation:
    """Represents a saved aggregation configuration and its resulting dataframe."""
    name: str
    description: str
    group_by: List[str]
    agg_config: Dict[str, str]
    date_grouping: Optional[Dict[str, str]] = None
    result_df: Optional[pd.DataFrame] = None
    created_at: datetime = field(default_factory=datetime.now)
    row_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converts the aggregation metadata to a dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "group_by": self.group_by,
            "agg_config": self.agg_config,
            "date_grouping": self.date_grouping,
            "created_at": self.created_at.isoformat(),
            "row_count": self.row_count
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

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            group_by=list(data.get("group_by", [])),
            agg_config=dict(agg_config),
            date_grouping=dict(data["date_grouping"]) if data.get("date_grouping") else None,
            created_at=created_at,
            row_count=data.get("row_count", 0)
        )

class AggregationManager:
    """Manages saved data aggregations, allowing storage, retrieval, and reapplication."""

    def __init__(self) -> None:
        self.saved_aggregations: Dict[str, SavedAggregation] = {}
    
    def save_aggregation(self, name: str, description: str, group_by: List[str], agg_config: Dict[str, str], result_df: pd.DataFrame, date_grouping: Optional[Dict[str, str]] = None) -> SavedAggregation:
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
            row_count=len(result_df)
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
        if name in self.saved_aggregations:
            del self.saved_aggregations[name]
            return True
        return False
    
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
        missing_group_cols = [col for col in agg.group_by if col not in df.columns]
        if missing_group_cols:
            raise KeyError(f"Cannot reapply aggregation. Missing grouping columns: {missing_group_cols}")

        missing_agg_cols = [col for col in agg.agg_config.keys() if col not in df.columns]
        if missing_agg_cols:
            raise KeyError(f"Cannot reapply aggregation. Missing aggregation columns: {missing_agg_cols}")
        
        try:
            # Apply standard pandas aggregation mapping
            result = df.groupby(agg.group_by, dropna=False).agg(agg.agg_config).reset_index()
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