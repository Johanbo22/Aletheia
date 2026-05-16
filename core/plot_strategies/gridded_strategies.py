import numpy as np
from core.plot_strategies.shared_strategies import GriddedPlotStrategy

class ImshowPlotStrategy(GriddedPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Image Show (imshow)"

    def _render_plot(self, engine, X, Y, Z, axes_flipped: bool, z_col: str, **kwargs):
        if axes_flipped:
            X, Y = Y, X
            Z = Z.T
        img = engine.current_ax.imshow(Z, extent=[X.min(), X.max(), Y.min(), Y.max()], origin="lower", aspect="auto", **kwargs)
        engine.current_figure.colorbar(img, ax=engine.current_ax, label=z_col)

class PColormeshPlotStrategy(GriddedPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "pcolormesh"

    def _render_plot(self, engine, X, Y, Z, axes_flipped: bool, z_col: str, **kwargs):
        if axes_flipped:
            X, Y = Y, X
            Z = Z.T
        X_grid, Y_grid = np.meshgrid(X, Y)
        mesh = engine.current_ax.pcolormesh(X_grid, Y_grid, Z, **kwargs)
        engine.current_figure.colorbar(mesh, ax=engine.current_ax, label=z_col)

class ContourPlotStrategy(GriddedPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Contour"

    def _render_plot(self, engine, X, Y, Z, axes_flipped: bool, z_col: str, **kwargs):
        if axes_flipped:
            X, Y = Y, X
            Z = Z.T
        X_grid, Y_grid = np.meshgrid(X, Y)
        cont = engine.current_ax.contour(X_grid, Y_grid, Z, **kwargs)
        engine.current_ax.clabel(cont, inline=True, fontsize=8)

class ContourFPlotStrategy(GriddedPlotStrategy):
    @property
    def plot_name(self) -> str:
        return "Contourf"

    def _render_plot(self, engine, X, Y, Z, axes_flipped: bool, z_col: str, **kwargs):
        if axes_flipped:
            X, Y = Y, X
            Z = Z.T
        X_grid, Y_grid = np.meshgrid(X, Y)
        contf = engine.current_ax.contourf(X_grid, Y_grid, Z, **kwargs)
        engine.current_figure.colorbar(contf, ax=engine.current_ax, label=z_col)