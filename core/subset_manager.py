#core/subset_manager
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import shutil
import tempfile
import atexit
from pathlib import Path

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
            logic=data.get("logic", "AND"),
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
            except Exception as CacheRemovalError:
                print(f"Error deleting cache: {CacheRemovalError}")
    
    def _get_cache_path(self, name: str) -> Path:
        """Retrieve the path for the cache file"""
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        return self.cached_directory / f"{safe_name}.parquet"
    
    def create_subset(self, name: str, description: str, filters: List[Dict[str, Any]], logic: str = "AND") -> Subset:
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
            except Exception as CacheReadError:
                print(f"WARNING: Failed to read cached data for {name}: {CacheReadError}")
        
        subset = self.subsets[name]
        filtered_df = self._apply_filters(df, subset.filters, subset.logic)

        subset.row_count = len(filtered_df)

        if use_cache:
            try:
                self.cached_directory.mkdir(parents=True, exist_ok=True)
                filtered_df.to_parquet(cache_path, index=False)
            except Exception as ParquetWriteError:
                print(f"WARNING: Failed to write cache file for subset {name} to disk: {ParquetWriteError}")
            
        return filtered_df
    
    def _apply_filters(self, df: pd.DataFrame, filters: List[Dict[str, Any]], logic: str) -> pd.DataFrame:
        """APpply all filters"""
        if not filters:
            return df.copy()
        
        if logic == "COMPLEX":
            current_mask = self._get_filter_mask(df, filters[0])
            for i in range(1, len(filters)):
                current_filter = filters[i]
                next_mask = self._get_filter_mask(df, current_filter)
                operator = current_filter.get("operator", "AND")
                
                if operator == "AND":
                    current_mask = current_mask & next_mask
                elif operator == "OR":
                    current_mask = current_mask | next_mask
            return df[current_mask]
        
        if logic == "AND":
            # apply filters in sequence
            result = df.copy()
            for filter in filters:
                result = self._apply_single_filter(result, filter)
            return result
        else:
            mask = pd.Series(False, index=df.index, dtype=bool)
            for filter in filters:
                filtered = self._apply_single_filter(df, filter)
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
        
        if condition == ">": return df[column] > value
        elif condition == "<": return df[column] < value
        elif condition == "==": return df[column] == value
        elif condition == "!=": return df[column] != value
        elif condition == ">=": return df[column] >= value
        elif condition == "<=": return df[column] <= value
        elif condition == "contains": return df[column].astype(str).str.contains(str(value), na=False)
        elif condition == "in": return df[column].isin(value if isinstance(value, list) else [value])
        
        return pd.Series([False] * len(df), index=df.index)
    
    def _apply_single_filter(self, df: pd.DataFrame, filter_def: Dict[str, Any]) -> pd.DataFrame:
        """Apply a singulear filter to df"""
        mask = self._get_filter_mask(df, filter_def)
        return df[mask]
    
    def clear_cache(self, name: Optional[str] = None) -> None:
        """Clear cached subset data"""
        if name:
            cache_path = self._get_cache_path(name)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except OSError as delete_cached_error:
                    print(f"WARNING: Failed to deleted cached directory at {cache_path}: {delete_cached_error}")
        else:
            if self.cached_directory.exists():
                for file_path in self.cached_directory.glob("*.parquet"):
                    try:
                        file_path.unlink()
                    except OSError as delete_cached_directory_error:
                        print(f"WARNING: Failed to delete {file_path}: {delete_cached_directory_error}")
    
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
        Create multiple subsets based on unique values in a column.
        useful for splitting data by more columns such as location, category etc.

        Returns a list of created subset names
        """
        if column not in df.columns:
            raise ValueError(f"Column: {column} not found in DataFrame")
        
        unique_values = df[column].unique()
        created_subsets = []

        for value in unique_values:
            #create a safe name fot the subset
            subset_name = f"{prefix}{column}_{value}".replace(" ", "_")

            #skip if the subset already exists
            if subset_name in self.subsets:
                continue

            #create filter
            filters = [{
                "column": column,
                "condition": "==",
                "value": value
            }]

            #create the subset
            try:
                self.create_subset(
                    name=subset_name,
                    description=f"Auto Created subset: {column} = {value}",
                    filters=filters,
                    logic="AND"
                )
                created_subsets.append(subset_name)
            except ValueError:
                continue
        
        return created_subsets