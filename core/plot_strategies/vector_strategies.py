import numpy as np
import pandas as pd
from core.plot_strategies.shared_strategies import VectorPlotStrategy

class BarbsPlotStrategy(VectorPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Barbs"

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, u_col: str, v_col: str, axes_flipped: bool,
                     **kwargs):
        if axes_flipped:
            engine.current_ax.barbs(df[y_col], df[x_col], df[v_col], df[u_col], **kwargs)
        else:
            engine.current_ax.barbs(df[x_col], df[y_col], df[u_col], df[v_col], **kwargs)


class QuiverPlotStrategy(VectorPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Quiver"

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, u_col: str, v_col: str, axes_flipped: bool,
                     **kwargs):
        if axes_flipped:
            engine.current_ax.quiver(df[y_col], df[x_col], df[v_col], df[u_col], **kwargs)
        else:
            engine.current_ax.quiver(df[x_col], df[y_col], df[u_col], df[v_col], **kwargs)


class StreamplotPlotStrategy(VectorPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Streamplot"

    def _prepare_gridded_data(self, df: pd.DataFrame, x: str, y: str, z: str):
        try:
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
        except Exception as e:
            raise ValueError(f"Streamplot data could not be pivoted into a 2D grid. Error: {str(e)}")

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, u_col: str, v_col: str, axes_flipped: bool,
                     **kwargs):
        X, Y, U_grid = self._prepare_gridded_data(df, x_col, y_col, u_col)
        _, _, V_grid = self._prepare_gridded_data(df, x_col, y_col, v_col)

        if axes_flipped:
            X, Y = Y, X
            U_grid = U_grid.T
            V_grid = V_grid.T
            X_grid, Y_grid = np.meshgrid(X, Y)
            engine.current_ax.streamplot(X_grid, Y_grid, V_grid, U_grid, **kwargs)
        else:
            X_grid, Y_grid = np.meshgrid(X, Y)
            engine.current_ax.streamplot(X_grid, Y_grid, U_grid, V_grid, **kwargs)