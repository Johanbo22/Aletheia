# core/plot_engine.py
"""
Plot Engine module for managing all plotting functionality

This module provides the PlotEngine class which handles plot generation using
matplotlib. This class is also responsible for rendering of canvas, ax and figure.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from core.plot_engine_objects.plot_analytics_renderer import PlotAnalyticsRenderer
from core.plot_engine_objects.plot_formatter import PlotFormatter
from core.plot_engine_objects.plot_layout_manager import PlotLayoutManager
from core.plot_engine_objects.plot_metadata import AVAILABLE_PLOTS, PLOT_DESCRIPTIONS
from core.plot_engine_objects.plot_table_renderer import PlotTableRenderer
from core.plot_engine_objects.secondary_axis_manager import SecondaryAxisManager
from core.regression_analyser import RegressionMetrics

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class PlotEngine:
    """
    Manages all plotting functionality
    API serves as a backend facade to Aletheias UI.

    plot_engine_objects module has each component of the engine
    """

    AVAILABLE_PLOTS = AVAILABLE_PLOTS
    PLOT_DESCRIPTIONS = PLOT_DESCRIPTIONS

    def __init__(self):
        self.current_figure: Optional[Figure] = None
        self.current_ax = None
        self.axes_flat = []
        self.current_plot_type: Optional[str] = None
        self.plot_config: Dict[str, Any] = {}
        self.secondary_ax = None
        self._cached_processed_data: Optional[pd.DataFrame] = None
        self._is_data_dirty: bool = False

        self._layout_manager = PlotLayoutManager(self)
        self._secondary_axis_manager = SecondaryAxisManager(self)
        self._table_renderer = PlotTableRenderer(self)
        self._formatter = PlotFormatter(self)
        self._analytics = PlotAnalyticsRenderer(self)
    
    def cache_data(self, df: pd.DataFrame) -> None:
        self._cached_processed_data = df.copy() if df is not None else None
        self._is_data_dirty = False
        
    def get_cached_data(self) -> Optional[pd.DataFrame]:
        return self._cached_processed_data
    
    def create_figure(self, figsize=(10, 6), dpi=100) -> Figure:
        """Create a new matplotlib figure"""
        return self._layout_manager.create_figure(figsize, dpi)

    def _set_labels(self, title: Optional[str], xlabel: Optional[str], ylabel: Optional[str], legend: bool, **kwargs) -> None:
        """Function that sets labels and handles latex rendering if requqested"""
        self._formatter.set_labels(title, xlabel, ylabel, legend, **kwargs)
    
    def finalize_layout(self) -> None:
        self._layout_manager.finalize_layout()

    def setup_layout(self, rows: int = 1, cols: int = 1, sharex: bool = False, sharey: bool = False, custom_grid: Optional[List[Tuple[int, int, int, int]]] = None) -> None:
        """Subplot layout grid"""
        self._layout_manager.setup_layout(rows, cols, sharex, sharey, custom_grid)

    def set_active_subplot(self, index: int):
        """Set the active subplot"""
        self._layout_manager.set_active_subplot(index)
        
    def clear_current_axis(self):
        """Clear the active subplot"""
        self._layout_manager.clear_current_axis()
    
    def get_active_axis_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """Function to calculate Qt geometry for the active axis relative to the current canvas"""
        return self._layout_manager.get_active_axis_geometry()
    
    def _get_colors_from_cmap(self, cmap_name, n_colors):
        """Generate a list of colors from a cmap"""
        if not cmap_name:
            return None
        
        try:
            cmap = matplotlib.colormaps[cmap_name]
            return [cmap(i) for i in np.linspace(0, 1, n_colors)]
        except KeyError:
            return None
    
    def _clear_axes(self):
        self._layout_manager.clear_axes()
    
    def _handle_secondary_axis(self, df: pd.DataFrame, x: str, secondary_y: str, secondary_plot_type: str, **kwargs) -> Any:
        """
        Method to handle plotting data on a secondary y axis (TwinX)
        Returns the secondary axis objet
        """
        self._secondary_axis_manager.handle_secondary_axis(df, x, secondary_y, secondary_plot_type, **kwargs)

    def _consolidate_legends(self, ax1, ax2):
        """Combine legends from primary and secondary axes into one"""
        self._secondary_axis_manager.consolidate_legends(ax1, ax2)

    def add_table(self, df: pd.DataFrame, loc='bottom', auto_font_size=False, fontsize=10, scale_factor=1.2, **kwargs) -> None:
        """Adding tables to the plot area"""
        self._table_renderer.add_table(df, loc, auto_font_size, fontsize, scale_factor, **kwargs)
    
    def clear_plot(self) -> None:
        """Clear the current plot"""
        if self.current_figure:
            self.setup_layout(1, 1)
    
    def get_figure(self) -> Figure:
        """Return the current figure"""
        return self.current_figure

    def _helper_format_categorical_axis(self, axis, labels):
        """Format categorical axis with better tick spacing"""
        self._formatter.format_categorical_axis(axis, labels)

    def _helper_is_datetime_column(self, plot_tab: "PlotTab", data: Any) -> bool:
        """Check if data is datetime"""
        return self._formatter.is_datetime_column(plot_tab, data)

    def _helper_apply_auto_datetime_format(self, plot_tab: "PlotTab", axis, data):
        """Apply datetime formatting based on the input datarange"""
        self._formatter.apply_auto_datetime_format(plot_tab, axis, data)

    def _helper_set_intelligent_locator(self, plot_tab: "PlotTab", axis, data):
        """Set tick locators based on tghe datarange"""
        self._formatter.set_intelligent_locator(plot_tab, axis, data)
    
    def _helper_format_datetime_axis(self, plot_tab: "PlotTab", ax, x_data, y_data=None) -> None:
        """Format datetime axes with tick spacing"""
        self._formatter.format_datetime_axis(plot_tab, ax, x_data, y_data)
    
    def _helper_apply_flipped_labels(self, plot_tab: "PlotTab", x_col, y_cols, font_family):
        """Function to correctly apply axes labels when flipped axes is true"""
        self._formatter.apply_flipped_labels(plot_tab, x_col, y_cols, font_family)

    def _helper_add_regression_analysis(self, plot_tab: "PlotTab", x_col: str, y_col: str,
                                        flipped: bool = False) -> None:
        """Orchestrates regression calculation via RegressionAnalyzer and renders output."""
        self._analytics.add_regression_analysis(plot_tab, x_col, y_col, flipped)
    
    def _render_regression_line(self, x_line: np.ndarray, y_line: np.ndarray, reg_type: Any, flipped: bool) -> None:
        self._analytics.render_regression_line(x_line, y_line, reg_type, flipped)
    
    def _render_confidence_interval(self, x_line: np.ndarray, y_line: np.ndarray, margin: np.ndarray, confidence: float, flipped: bool) -> None:
        self._analytics.render_confidence_interval(x_line, y_line, margin, confidence, flipped)
    
    def _render_regression_statistics(self, plot_tab: 'PlotTab', metrics: RegressionMetrics, flipped: bool) -> None:
        self._analytics.render_regression_statistics(plot_tab, metrics, flipped)
    
    def add_error_bars(self, df: pd.DataFrame, x_col: str, y_cols: List[str], error_bar_type_str: str, flipped: bool = False, plot_tab: "PlotTab" = None) -> None:
        """Computes standard deviation and standard error bars"""
        self._analytics.add_error_bars(df, x_col, y_cols, error_bar_type_str, flipped, plot_tab)
    
    def _ensure_projection(self, is_3d: bool) -> None:
        """Replaces the current axis with 3D or 2D"""
        self._layout_manager.ensure_projection(is_3d)
    
    # Plot strategies
    def execute_strategy(self, plot_type: str, plot_tab: "PlotTab", x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        from core.plot_strategies.strat_registry import StrategyRegistry
        try:
            is_3d_plot = plot_type in ["3D Scatter", "3D Line", "3D Surface"]
            self._ensure_projection(is_3d_plot)
            
            strategy = StrategyRegistry.get_strategy(plot_type)
            return strategy.execute(
                engine=self,
                plot_tab=plot_tab,
                x_col=x_col,
                y_cols=y_cols,
                axes_flipped=axes_flipped,
                font_family=font_family,
                plot_kwargs=plot_kwargs,
                general_kwargs=general_kwargs
            )
        except ValueError as error:
            return str(error)
        except Exception as error:
            return f"Failed to execute plotting sequence for {plot_type}. Error: {str(error)}"