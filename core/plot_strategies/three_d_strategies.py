from typing import Dict, Any, List, Optional, TYPE_CHECKING
import pandas as pd
import numpy as np
from core.plot_strategies.base_strategy import BasePlotStrategy

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab


def _validate_3d_columns(df: pd.DataFrame, x_col: str, y_col: str, z_col: str) -> Optional[str]:
    """Ensures that the selected columns are strictly numeric to prevent mplot3d projection crashes."""
    for col, axis in [(x_col, 'X'), (y_col, 'Y'), (z_col, 'Z')]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return f"3D Plotting Error: The {axis} Column '{col}' is not numeric. 3D plots strictly require numerical data."
    return None


class Scatter3DStrategy(BasePlotStrategy):
    """Strategy for executing 3D Scatter plots."""

    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool,
                font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
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

        engine._clear_axes()

        title = general_kwargs.pop("title", None)
        xlabel = general_kwargs.pop("xlabel", None)
        ylabel = general_kwargs.pop("ylabel", None)
        zlabel = general_kwargs.pop("zlabel", None)
        legend = general_kwargs.pop("legend", True)
        hue = general_kwargs.pop("hue", None)
        cmap_name = general_kwargs.pop("cmap", general_kwargs.pop("palette", None))

        kwargs = plot_kwargs.copy()
        kwargs.pop("secondary_y", None)
        kwargs.pop("secondary_plot_type", None)

        elevation = kwargs.pop("elevation", general_kwargs.pop("elevation", None))
        azimuth = kwargs.pop("azimuth", general_kwargs.pop("azimuth", None))

        if elevation is not None or azimuth is not None:
            engine.current_ax.view_init(elev=elevation, azim=azimuth)

        mask = df[x_col].notna() & df[y_col].notna() & df[z_col].notna()

        if hue and hue in df.columns:
            groups = df[hue].dropna().unique()
            colors = engine._get_colors_from_cmap(cmap_name, len(groups))

            for i, group in enumerate(groups):
                group_mask = mask & (df[hue] == group)
                c = colors[i] if colors else None
                engine.current_ax.scatter3D(
                    df.loc[group_mask, x_col].to_numpy(),
                    df.loc[group_mask, y_col].to_numpy(),
                    df.loc[group_mask, z_col].to_numpy(),
                    label=str(group), color=c, picker=5, **kwargs
                )
        else:
            if cmap_name: kwargs["cmap"] = cmap_name
            engine.current_ax.scatter3D(
                df.loc[mask, x_col].to_numpy(),
                df.loc[mask, y_col].to_numpy(),
                df.loc[mask, z_col].to_numpy(),
                picker=5, **kwargs
            )

        engine._set_labels(title, xlabel, ylabel, legend, zlabel=zlabel, **general_kwargs)
        return None


class Line3DStrategy(BasePlotStrategy):
    """Strategy for executing 3D Line plots."""

    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool,
                font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
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

        engine._clear_axes()

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        zlabel = general_kwargs.pop('zlabel', None)
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop("cmap", general_kwargs.pop("palette", None))

        kwargs = plot_kwargs.copy()
        kwargs.pop("secondary_y", None)
        kwargs.pop("secondary_plot_type", None)

        elevation = kwargs.pop("elevation", general_kwargs.pop("elevation", None))
        azimuth = kwargs.pop("azimuth", general_kwargs.pop("azimuth", None))

        if elevation is not None or azimuth is not None:
            engine.current_ax.view_init(elev=elevation, azim=azimuth)

        mask = df[x_col].notna() & df[y_col].notna() & df[z_col].notna()

        if hue and hue in df.columns:
            groups = df[hue].dropna().unique()
            colors = engine._get_colors_from_cmap(cmap_name, len(groups))

            for i, group in enumerate(groups):
                group_mask = mask & (df[hue] == group)
                c = colors[i] if colors else None
                engine.current_ax.plot3D(
                    df.loc[group_mask, x_col].to_numpy(),
                    df.loc[group_mask, y_col].to_numpy(),
                    df.loc[group_mask, z_col].to_numpy(),
                    label=str(group), color=c, picker=5, **kwargs
                )
        else:
            colors = engine._get_colors_from_cmap(cmap_name, 1)
            c = colors[0] if colors else None
            if c: kwargs["color"] = c
            engine.current_ax.plot3D(
                df.loc[mask, x_col].to_numpy(),
                df.loc[mask, y_col].to_numpy(),
                df.loc[mask, z_col].to_numpy(),
                label=f"{y_col} vs {z_col}", picker=5, **kwargs
            )

        engine._set_labels(title, xlabel, ylabel, legend, zlabel=zlabel, **general_kwargs)
        return None


class Surface3DStrategy(BasePlotStrategy):
    """Strategy for executing 3D Surface plots."""

    def _prepare_gridded_data(self, df: pd.DataFrame, x: str, y: str, z: str):
        if df[[x, y]].duplicated().any():
            df_agg = df.groupby([x, y])[z].mean().reset_index()
        else:
            df_agg = df

        pivot_df = df_agg.pivot(index=y, columns=x, values=z)
        pivot_df = pivot_df.sort_index(axis=0).sort_index(axis=1)

        X = pivot_df.columns.values
        Y = pivot_df.index.values
        Z = pivot_df.values
        return X, Y, Z

    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool,
                font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
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

        engine._clear_axes()

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        zlabel = general_kwargs.pop('zlabel', None)
        _ = general_kwargs.pop("legend", None)
        cmap_name = general_kwargs.pop("cmap", general_kwargs.pop("palette", "viridis"))

        kwargs = plot_kwargs.copy()
        kwargs.pop("secondary_y", None)
        kwargs.pop("secondary_plot_type", None)

        elevation = kwargs.pop("elevation", general_kwargs.pop("elevation", None))
        azimuth = kwargs.pop("azimuth", general_kwargs.pop("azimuth", None))

        if elevation is not None or azimuth is not None:
            engine.current_ax.view_init(elev=elevation, azim=azimuth)

        try:
            X, Y, Z = self._prepare_gridded_data(df, x_col, y_col, z_col)
            X_grid, Y_grid = np.meshgrid(X, Y)

            surf = engine.current_ax.plot_surface(X_grid, Y_grid, Z, cmap=cmap_name, **kwargs)
            engine.current_figure.colorbar(surf, ax=engine.current_ax, label=zlabel if zlabel else z_col)

            engine._set_labels(title, xlabel, ylabel, False, zlabel=zlabel, **general_kwargs)
            return None
        except Exception as err:
            return f"Surface plot failed to prepare gridded data: {str(err)}"