from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class ViolinPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(f"Violin plots support only one y column. Using {y_cols[0]}", "WARNING")

        y_col = y_cols[0]

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        kwargs = plot_kwargs.copy()

        import seaborn as sns

        if cmap_name:
            kwargs["palette"] = cmap_name

        kwargs["picker"] = kwargs.get("picker", True)

        if axes_flipped:
            sns.violinplot(data=df, x=y_col, y=x_col, hue=hue, ax=engine.current_ax, orient="h", **kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
        else:
            sns.violinplot(data=df, x=x_col, y=y_col, hue=hue, ax=engine.current_ax, orient="v", **kwargs)
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_col], df[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], df[y_col])
        except Exception:
            pass

        return None