#core/subset_manager
"""
Subset Manager module for managing data subsets and filter configurations.

This module provides the SubsetManager class which handles creating, storing,
and managing data subsets
"""
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import shutil
import tempfile
import atexit
from pathlib import Path
from enum import Enum

class FilterLogic(str, Enum):
    AND = "AND"
    OR = "OR"
    COMPLEX = "COMPLEX"

class FilterCondition(str, Enum):
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    IS_NULL = "Is Null"
    IS_NOT_NULL = "Is Not Null"
    CONTAINS = "contains"
    IN = "in"

@dataclass
class Subset:
    """A Named subset of data with filtering criteria"""
    name: str
    description: str
    filters: List[Dict[str, Any]]
    logic: str = "AND"
    created_at: datetime = field(default_factory=datetime.now)
    row_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert subset to dict for saving"""
        return {
            "name": self.name,
            "description": self.description,
            "filters": self.filters,
            "logic": self.logic,
            "created_at": self.created_at,
            "row_count": self.row_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subset":
        """Create a subset from dict"""
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        return cls(
            name=data["name"],
            description=data["description"],
            filters=data["filters"],
            logic=data.get("logic", FilterLogic.AND.value),
            created_at=created_at,
            row_count=data.get("row_count", 0)
        )

class SubsetManager:
    """Creates, stores and uses data subsets"""

    def __init__(self):
        self.subsets: Dict[str, Subset] = {}
        self.cached_directory = Path(tempfile.mkdtemp(prefix="dps_subset_cache_"))
        atexit.register(self._cleanup_cache)
    
    def _cleanup_cache(self):
        """Deletes files from the tempfile directory on exit"""
        if self.cached_directory.exists():
            try:
                shutil.rmtree(self.cached_directory)
            except Exception as error:
                print(f"Error deleting cache: {error}")
    
    def _get_cache_path(self, name: str) -> Path:
        """Retrieve the path for the cache file"""
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        return self.cached_directory / f"{safe_name}.parquet"
    
    def create_subset(self, name: str, description: str, filters: List[Dict[str, Any]], logic: str = FilterLogic.AND.value) -> Subset:
        """Create a new subset definition"""
        if name in self.subsets:
            raise ValueError(f"Subset '{name}' already exists")
        
        subset = Subset(
            name=name,
            description=description,
            filters=filters,
            logic=logic
        )
        
        self.subsets[name] = subset
        return subset
    
    def update_subset(self, name: str, description: Optional[str] = None, filters: Optional[List[Dict[str, Any]]] = None, logic: Optional[str] = None) -> Subset:
        """Update existing subset"""
        if name not in self.subsets:
            raise ValueError(f"Subset '{name} does not exists'")
        
        subset = self.subsets[name]
        if description is not None:
            subset.description = description
        if filters is not None:
            subset.filters = filters
        if logic is not None:
            subset.logic = logic
        
        #invalidate cache
        self.clear_cache(name)
        
        return subset
    
    def delete_subset(self, name: str) -> bool:
        """Delete a subset"""
        if name in self.subsets:
            del self.subsets[name]
            self.clear_cache(name)
            return True
        return False
    
    def get_subset(self, name: str) -> Optional[Subset]:
        """Get subset definition"""
        return self.subsets.get(name)
    
    def list_subsets(self) -> List[str]:
        """List all subsets"""
        return list(self.subsets.keys())
    
    def apply_subset(self, df: pd.DataFrame, name: str, use_cache: bool = True) -> pd.DataFrame:
        """Apply subset filters to dataframe and return the filtered data"""
        if name not in self.subsets:
            raise ValueError(f"Subset '{name}' does not exist")
        
        df_state_hash = hash(f"{df.shape}_{list(df.columns)}")
        cache_key = f"{name}_{df_state_hash}"
        cache_path = self._get_cache_path(cache_key)
        
        if use_cache and cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception as error:
                print(f"WARNING: Failed to read cached data for {name}: {error}")
        
        subset = self.subsets[name]
        filtered_df = self._apply_filters(df, subset.filters, subset.logic)

        subset.row_count = len(filtered_df)

        if use_cache:
            try:
                self.cached_directory.mkdir(parents=True, exist_ok=True)
                filtered_df.to_parquet(cache_path, index=False)
            except Exception as error:
                print(f"WARNING: Failed to write cache file for subset {name} to disk: {error}")
            
        return filtered_df
    
    def _apply_filters(self, df: pd.DataFrame, filters: List[Dict[str, Any]], logic: str) -> pd.DataFrame:
        """APpply all filters"""
        if not filters:
            return df.copy()
        
        if logic == FilterLogic.COMPLEX.value:
            current_mask = self._get_filter_mask(df, filters[0])
            for i in range(1, len(filters)):
                current_filter = filters[i]
                next_mask = self._get_filter_mask(df, current_filter)
                operator = current_filter.get("operator", FilterLogic.AND.value)
                
                if operator == FilterLogic.AND.value:
                    current_mask = current_mask & next_mask
                elif operator == FilterLogic.OR.value:
                    current_mask = current_mask | next_mask
            return df[current_mask]
        
        if logic == FilterLogic.AND.value:
            # apply filters in sequence
            result = df.copy()
            for filter_def in filters:
                result = self._apply_single_filter(result, filter_def)
            return result
        else:
            mask = pd.Series(False, index=df.index, dtype=bool)
            for filter_def in filters:
                filtered = self._apply_single_filter(df, filter_def)
                mask = mask | df.index.isin(filtered.index)
            return df[mask]
    
    def _get_filter_mask(self, df: pd.DataFrame, filter_def: Dict[str, Any]) -> pd.Series:
        """Setup a boolean mask for a single filter"""
        column = filter_def["column"]
        condition = filter_def["condition"]
        value = filter_def["value"]
        
        if column not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        
        if condition == "Is Null":
            return df[column].isna()
        if condition == "Is Not Null":
            return df[column].notna()
        
        if value is not None:
            col_dtype = df[column].dtype
            try:
                if pd.api.types.is_integer_dtype(col_dtype):
                    value = int(value)
                elif pd.api.types.is_float_dtype(col_dtype):
                    value = float(value)
            except (TypeError, ValueError):
                pass

        if condition == FilterCondition.GREATER_THAN.value:
            return df[column] > value
        elif condition == FilterCondition.LESS_THAN.value:
            return df[column] < value
        elif condition == FilterCondition.EQUALS.value:
            return df[column] == value
        elif condition == FilterCondition.NOT_EQUALS.value:
            return df[column] != value
        elif condition == FilterCondition.GREATER_EQUAL.value:
            return df[column] >= value
        elif condition == FilterCondition.LESS_EQUAL.value:
            return df[column] <= value
        elif condition == FilterCondition.CONTAINS.value:
            return df[column].astype(str).str.contains(str(value), na=False)
        elif condition == FilterCondition.IN.value:
            return df[column].isin(value if isinstance(value, list) else [value])
        
        return pd.Series([False] * len(df), index=df.index)
    
    def _apply_single_filter(self, df: pd.DataFrame, filter_def: Dict[str, Any]) -> pd.DataFrame:
        """Apply a singular filter to the DataFrame"""
        mask = self._get_filter_mask(df, filter_def)
        return df[mask]
    
    def clear_cache(self, name: Optional[str] = None) -> None:
        """
        Clear cached subset data
        If name is provided, clears all caches mapped to that specific subset
        """
        if not self.cached_directory.exists():
            return

        if name:
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
            for file_path in self.cached_directory.glob(f"{safe_name}_*.parquet"):
                try:
                    file_path.unlink()
                except OSError as e:
                    print(f"WARNING: Failed to delete cache file {file_path}: {e}")
        else:
            for file_path in self.cached_directory.glob("*.parquet"):
                try:
                    file_path.unlink()
                except OSError as e:
                    print(f"WARNING: Failed to delete cache file {file_path}: {e}")
    
    def get_subset_info(self, name: str) -> Dict[str, Any]:
        """Get info about a subset"""
        if name not in self.subsets:
            raise ValueError(f"Subset '{name}' does not exist")
        
        subset = self.subsets[name]
        cache_path = self._get_cache_path(name)
        return {
            "name": subset.name,
            "description": subset.description,
            "filters": subset.filters,
            "logic": subset.logic,
            "created_at": subset.created_at,
            "row_count": subset.row_count,
            "is_cached": cache_path.exists()
        }
    
    def export_subsets(self) -> Dict[str, Any]:
        """Export all subsets"""
        return {
            name: subset.to_dict()
            for name, subset in self.subsets.items()
        }

    def import_subsets(self, data: Dict[str, Any]):
        """Import subsets"""
        self.subsets.clear()
        self.clear_cache()

        if data is None:
            return

        for name, subset_data in data.items():
            self.subsets[name] = Subset.from_dict(subset_data)

    def create_subset_from_unique_values(self, df: pd.DataFrame, column: str, prefix: str = "") -> List[str]:
        """
        Create multiple subsets based on unique values in a column
        Useful for splitting data by more columns such as location, category etc.

        :param df: The DataFrame to evaluate
        :param column: The column to find unique values in
        :param prefix: Optional prefix for the subset names
        :return: A list of created subset names
        """
        if column not in df.columns:
            raise ValueError(f"Column: {column} not found in DataFrame")
        
        unique_values = df[column].unique()
        created_subsets = []

        for value in unique_values:
            is_null_val = pd.isna(value)
            val_str = "NaN" if is_null_val else str(value)

            #create a safe name fot the subset
            subset_name = f"{prefix}{column}_{value}".replace(" ", "_")

            #skip if the subset already exists
            if subset_name in self.subsets:
                continue

            #create filter
            filters = [{
                "column": column,
                "condition": FilterCondition.IS_NULL.value if is_null_val else FilterCondition.EQUALS.value,
                "value": value
            }]

            #create the subset
            try:
                self.create_subset(
                    name=subset_name,
                    description=f"Auto Created subset: {column} = {val_str}",
                    filters=filters,
                    logic=FilterLogic.AND.value
                )
                created_subsets.append(subset_name)
            except ValueError:
                continue
        
        return created_subsets