from abc import abstractmethod
import pandas as pd
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class GriddedPlotStrategy(BasePlotStrategy):
    """Base strategy for plots requireing gridded data"""
    @property
    @abstractmethod
    def plot_name(self) -> str:
        pass

    def _prepare_gridded_data(self, df: pd.DataFrame, x: str, y: str, z: str):
        """Helper func to pivot data for gridded plots"""
        try:
            df_grid = df[[x, y, z]].copy()
            df_grid[z] = pd.to_numeric(df_grid[z], errors="coerce")

            if df_grid[[x, y]].duplicated().any():
                df_agg = df_grid.groupby([x, y])[z].mean().reset_index()
            else:
                df_agg = df_grid

            pivot_df = df_agg.pivot(index=y, columns=x, values=z)
            pivot_df = pivot_df.sort_index(axis=0).sort_index(axis=1)

            X = pivot_df.columns.values
            Y = pivot_df.index.values
            Z = pivot_df.astype(float).values

            return X, Y, Z
        except Exception as GridDataError:
            raise ValueError(f"Could not grid data: {str(GridDataError)}")

    @abstractmethod
    def _render_plot(self, engine: 'PlotEngine', X, Y, Z, axes_flipped: bool, z_col: str, **kwargs):
        pass

    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool,
                font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        if len(y_cols) < 2:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(
                    f"{self.plot_name} requires a Z column. Please select a second Y column (Z-value).", "WARNING")
            return f"{self.plot_name} requires a Z column."

        df = plot_tab.data_handler.df
        engine._clear_axes()

        y_col = y_cols[0]  # Y-axis
        z_col = y_cols[1]  # Z-axis (color)

        title = general_kwargs.pop("title", None)

        xlabel_input = ""
        if hasattr(plot_tab, "xlabel_input"):
            xlabel_input = plot_tab.xlabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "xlabel_input"):
            xlabel_input = plot_tab.view.xlabel_input.text()

        ylabel_input = ""
        if hasattr(plot_tab, "ylabel_input"):
            ylabel_input = plot_tab.ylabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "ylabel_input"):
            ylabel_input = plot_tab.view.ylabel_input.text()

        xlabel = general_kwargs.pop("xlabel", xlabel_input or x_col)
        ylabel = general_kwargs.pop("ylabel", ylabel_input or y_col)
        _ = general_kwargs.pop("legend", None)
        cmap = general_kwargs.pop("cmap", general_kwargs.pop("palette", None))

        kwargs = plot_kwargs.copy()
        if cmap:
            kwargs["cmap"] = cmap

        kwargs["picker"] = kwargs.get("picker", True)

        X, Y, Z = self._prepare_gridded_data(df, x_col, y_col, z_col)

        self._render_plot(engine, X, Y, Z, axes_flipped, z_col, **kwargs)

        if axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_col], df[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], df[y_col])
        except Exception:
            pass

        return None

class VectorPlotStrategy(BasePlotStrategy):
    """Base strategy for vector fields requiring (X, Y, U, V)."""

    @property
    @abstractmethod
    def plot_name(self) -> str:
        pass

    @abstractmethod
    def _render_plot(self, engine: 'PlotEngine', df: pd.DataFrame, x_col: str, y_col: str, u_col: str, v_col: str,
                     axes_flipped: bool, **kwargs):
        pass

    def execute(
            self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str,
            y_cols: List[str], axes_flipped: bool, font_family: str,
            plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]
    ) -> Optional[str]:

        if len(y_cols) < 3:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(
                    f"{self.plot_name} requires 3 Y columns: Y-position, U (x-component), V (y-component).", "WARNING")
            return f"{self.plot_name} requires 3 Y columns: Y-position, U (x-component), V (y-component)."

        df = plot_tab.data_handler.df
        engine._clear_axes()

        y_col = y_cols[0]
        u_col = y_cols[1]
        v_col = y_cols[2]

        title = general_kwargs.pop("title", None)

        xlabel_input = ""
        if hasattr(plot_tab, "xlabel_input"):
            xlabel_input = plot_tab.xlabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "xlabel_input"):
            xlabel_input = plot_tab.view.xlabel_input.text()

        ylabel_input = ""
        if hasattr(plot_tab, "ylabel_input"):
            ylabel_input = plot_tab.ylabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "ylabel_input"):
            ylabel_input = plot_tab.view.ylabel_input.text()

        xlabel = general_kwargs.pop("xlabel", xlabel_input or x_col)
        ylabel = general_kwargs.pop("ylabel", ylabel_input or y_col)
        _ = general_kwargs.pop("legend", None)

        kwargs = plot_kwargs.copy()

        if general_kwargs.get("cmap"):
            kwargs["cmap"] = general_kwargs.pop("cmap")
        elif general_kwargs.get("palette"):
            kwargs["cmap"] = general_kwargs.pop("palette")

        kwargs["picker"] = kwargs.get("picker", True)

        self._render_plot(engine, df, x_col, y_col, u_col, v_col, axes_flipped, **kwargs)

        if axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_col], df[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], df[y_col])
        except Exception:
            pass

        return None

class TriangulationPlotStrategy(BasePlotStrategy):
    """Base strategy for unstructured triangulation plots."""

    @property
    @abstractmethod
    def plot_name(self) -> str:
        pass

    @abstractmethod
    def _render_plot(self, engine: 'PlotEngine', df: pd.DataFrame, x_col: str, y_col: str, z_col: Optional[str],
                     axes_flipped: bool, **kwargs):
        pass

    def execute(
            self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str,
            y_cols: List[str], axes_flipped: bool, font_family: str,
            plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]
    ) -> Optional[str]:

        if len(y_cols) < 2 and self.plot_name != "Triplot":
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(
                    f"{self.plot_name} requires a Z column. Please select a second Y column (Z-axis).", "WARNING")
            return f"{self.plot_name} requires a Z column."
        elif not y_cols and self.plot_name == "Triplot":
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(f"{self.plot_name} requires a Y column.", "WARNING")
            return f"{self.plot_name} requires a Y column."

        df = plot_tab.data_handler.df
        engine._clear_axes()

        y_col = y_cols[0]
        z_col = y_cols[1] if len(y_cols) > 1 else None

        title = general_kwargs.pop("title", None)

        xlabel_input = ""
        if hasattr(plot_tab, "xlabel_input"):
            xlabel_input = plot_tab.xlabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "xlabel_input"):
            xlabel_input = plot_tab.view.xlabel_input.text()

        ylabel_input = ""
        if hasattr(plot_tab, "ylabel_input"):
            ylabel_input = plot_tab.ylabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "ylabel_input"):
            ylabel_input = plot_tab.view.ylabel_input.text()

        xlabel = general_kwargs.pop("xlabel", xlabel_input or x_col)
        ylabel = general_kwargs.pop("ylabel", ylabel_input or y_col)
        _ = general_kwargs.pop("legend", None)
        cmap = general_kwargs.pop("cmap", general_kwargs.pop("palette", None))

        kwargs = plot_kwargs.copy()

        if cmap:
            kwargs["cmap"] = cmap

        kwargs["picker"] = kwargs.get("picker", True)

        self._render_plot(engine, df, x_col, y_col, z_col, axes_flipped, **kwargs)

        if axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_col], df[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], df[y_col])
        except Exception:
            pass

        return None