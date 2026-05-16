from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class HexbinPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(f"Hexbin plot only supports one y column. Using: {y_cols[0]}", "WARNING")

        y_col = y_cols[0] if y_cols else x_col

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        kwargs = plot_kwargs.copy()
        gridsize = kwargs.pop('gridsize', general_kwargs.pop('gridsize', 20))

        if cmap_name:
            kwargs["cmap"] = cmap_name

        kwargs["picker"] = kwargs.get("picker", True)

        mask = df[x_col].notna() & df[y_col].notna()
        x_data = df.loc[mask, x_col]
        y_data = df.loc[mask, y_col]

        if axes_flipped:
            engine.current_ax.hexbin(y_data, x_data, gridsize=gridsize, **kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
        else:
            engine.current_ax.hexbin(x_data, y_data, gridsize=gridsize, **kwargs)
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, y_data, x_data)
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, x_data, y_data)
        except Exception:
            pass

        return None