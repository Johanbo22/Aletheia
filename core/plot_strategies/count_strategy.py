from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class CountPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        kwargs = plot_kwargs.copy()

        if cmap_name:
            kwargs["palette"] = cmap_name

        import seaborn as sns

        kwargs["picker"] = kwargs.get("picker", True)

        if axes_flipped:
            sns.countplot(data=df, y=x_col, hue=hue, ax=engine.current_ax, **kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [], font_family)
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
        else:
            sns.countplot(data=df, x=x_col, hue=hue, ax=engine.current_ax, **kwargs)
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        if legend and hue:
            engine.current_ax.legend()

        return None
    