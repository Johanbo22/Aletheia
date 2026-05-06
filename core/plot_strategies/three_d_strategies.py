from typing import Dict, Any, List, Optional, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

def _validate_3d_columns(df: pd.DataFrame, x_col: str, y_col: str, z_col: str) -> Optional[str]:
    """Ensures that the selected columns are strictly numeric to prevent mplot3d projection crashes."""
    for col, axis in [(x_col, 'X'), (y_col, 'Y'), (z_col, 'Z')]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return f"3D Plotting Error: The {axis} Column '{col}' is not numeric. 3D plots strictly require numerical data."
    return None
    
class Scatter3DStrategy:
    """Strategy for executing 3D Scatter plots."""
    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        z_col = general_kwargs.pop("z_column", None)
        if not z_col or z_col == "None":
            return "3D Scatter plot requires a valid Z Column mapped from General Settings."
        if not y_cols:
            return "3D Scatter plot requires at least one Y Column."
        
        y_col = y_cols[0]
        df = engine.get_cached_data() if engine.get_cached_data() is not None else plot_tab.data_handler.df
        
        err = _validate_3d_columns(df, x_col, y_col, z_col)
        if err:
            return err
        
        engine.plot_scatter_3d(df, x_col, y_col, z_col, **general_kwargs, **plot_kwargs)
        return None

class Line3DStrategy:
    """Strategy for executing 3D Line plots."""
    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        z_col = general_kwargs.pop("z_column", None)
        if not z_col or z_col == "None":
            return "3D Line plot requires a valid Z Column mapped from General Settings."
        if not y_cols:
            return "3D Line plot requires at least one Y Column."
        
        y_col = y_cols[0]
        df = engine.get_cached_data() if engine.get_cached_data() is not None else plot_tab.data_handler.df
        
        err = _validate_3d_columns(df, x_col, y_col, z_col)
        if err: 
            return err
        
        engine.plot_line_3d(df, x_col, y_col, z_col, **general_kwargs, **plot_kwargs)
        return None

class Surface3DStrategy:
    """Strategy for executing 3D Surface plots."""
    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        z_col = general_kwargs.pop("z_column", None)
        if not z_col or z_col == "None":
            return "3D Surface plot requires a valid Z Column mapped from General Settings."
        if not y_cols:
            return "3D Surface plot requires at least one Y Column."
        
        y_col = y_cols[0]
        df = engine.get_cached_data() if engine.get_cached_data() is not None else plot_tab.data_handler.df
        
        err = _validate_3d_columns(df, x_col, y_col, z_col)
        if err: 
            return err
        
        try:
            engine.plot_surface_3d(df, x_col, y_col, z_col, **general_kwargs, **plot_kwargs)
            return None
        except ValueError as err:
            return f"Surface plot failed: {str(err)}"