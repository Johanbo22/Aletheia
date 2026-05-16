from core.plot_strategies.shared_strategies import TriangulationPlotStrategy
import pandas as pd


class TricontourPlotStrategy(TriangulationPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Tricontour"

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, z_col: str, axes_flipped: bool, **kwargs):
        if axes_flipped:
            cont = engine.current_ax.tricontour(df[y_col], df[x_col], df[z_col], **kwargs)
        else:
            cont = engine.current_ax.tricontour(df[x_col], df[y_col], df[z_col], **kwargs)
        engine.current_ax.clabel(cont, inline=True, fontsize=8)


class TricontourfPlotStrategy(TriangulationPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Tricontourf"

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, z_col: str, axes_flipped: bool, **kwargs):
        if axes_flipped:
            contf = engine.current_ax.tricontourf(df[y_col], df[x_col], df[z_col], **kwargs)
        else:
            contf = engine.current_ax.tricontourf(df[x_col], df[y_col], df[z_col], **kwargs)
        engine.current_figure.colorbar(contf, ax=engine.current_ax, label=z_col)


class TripcolorPlotStrategy(TriangulationPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Tripcolor"

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, z_col: str, axes_flipped: bool, **kwargs):
        if axes_flipped:
            trip = engine.current_ax.tripcolor(df[y_col], df[x_col], df[z_col], **kwargs)
        else:
            trip = engine.current_ax.tripcolor(df[x_col], df[y_col], df[z_col], **kwargs)
        engine.current_figure.colorbar(trip, ax=engine.current_ax, label=z_col)


class TriplotPlotStrategy(TriangulationPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Triplot"

    def _render_plot(self, engine, df: pd.DataFrame, x_col: str, y_col: str, z_col: str, axes_flipped: bool, **kwargs):
        if axes_flipped:
            engine.current_ax.triplot(df[y_col], df[x_col], **kwargs)
        else:
            engine.current_ax.triplot(df[x_col], df[y_col], **kwargs)