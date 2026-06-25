"""
Aggregation Manager is for managing saved data aggregations

Provides methods for storing, retrieving and reapplying
data aggregation configurations
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

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
        """
        Convert the aggregation metadata to a dictionary for serialization

        This method handles the storage of the aggregation configuration
        by exporting the dataclass attributes to a dictionary. The resulting
        DataFrame is excluded.

        :return: A dictionary representation of the saved aggregation metadata
        """
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
        """
        Create a SavedAggregation instance from a dictionary representation

        This class method is used during the deserialization of project files.
        It maintains older compatibility by checking for the older version of keys ("agg_columns" and "agg_func")
        if the primary "agg_config" is missing from project data

        :param data: The dictionary containing the aggregation metadata
        :return: A newly instantiated SavedAggregation object
        """
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
        """
        Creates an empty registry for storing SavedAggregation instances
        in memory, key by a name that has to be unique.
        """
        self.saved_aggregations: Dict[str, SavedAggregation] = {}
    
    def save_aggregation(self, name: str, description: str, group_by: List[str], agg_config: Dict[str, str], result_df: pd.DataFrame, date_grouping: Optional[Dict[str, str]] = None, rename_mapping: Optional[Dict[str, str]] = None) -> SavedAggregation:
        """
        Save a new aggregation configuration and its initial resulting DataFrame

        Stores the configuration necessary to reproduce the aggregation and keeps a copy of
        computed dataset for retrieval. Ensures names are unique to prevent overrides

        :param name: The unique identifier for the aggregation
        :param description: A summary of the aggregation's purpose
        :param group_by: A list of column names used to group the data
        :param agg_config: A mapping of column names to aggregation functions
        :param result_df: The DataFrame resulting from the initial aggregation
        :param date_grouping: Configurations for grouping by date components
        :param rename_mapping: Mapping for renaming columns in the result
        :raises ValueError: If an aggregation with the given name already exists
        :return: The newly created SavedAggregation instance
        """
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
        """
        Retrieve a saved aggregation by its name
        :param name: The name identifier for the aggregation to retrieve
        :return: The SavedAggregation instance if found, otherwise None
        """
        return self.saved_aggregations.get(name)
    
    def list_aggregations(self) -> List[str]:
        """
        Lists all stored aggregation names
        :return: A list of registered aggregation names
        """
        return list(self.saved_aggregations.keys())
    
    def delete_aggregation(self, name: str) -> bool:
        """
        Deletes an aggregation of the manager's registry
        :param name: The identifier of the aggregation to remove
        :return: True if the aggregation was found and deleted, False otherwise
        """
        return self.saved_aggregations.pop(name, None) is not None
    
    def get_aggregation_df(self, name: str) -> Optional[pd.DataFrame]:
        """
        Return a copy of the resulting DataFrame for a saved aggregation
        :param name: The identifier of the aggregation
        :return: A copy of the aggregated DataFrame if it exists else None
        """
        agg = self.saved_aggregations.get(name)
        return agg.result_df.copy() if agg and agg.result_df is not None else None