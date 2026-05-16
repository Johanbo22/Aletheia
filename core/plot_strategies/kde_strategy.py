from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class KDEPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(f"KDE plot typically supports one column. Using: {y_cols[0]}", "WARNING")

        data_col = y_cols[0] if y_cols else x_col

        title = general_kwargs.pop('title', None)

        # Try to get xlabel from input, fallback to data_col
        xlabel_input = ""
        if hasattr(plot_tab, "xlabel_input"):
            xlabel_input = plot_tab.xlabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "xlabel_input"):
            xlabel_input = plot_tab.view.xlabel_input.text()

        xlabel = general_kwargs.pop('xlabel', xlabel_input or data_col)
        ylabel = general_kwargs.pop('ylabel', "Density")
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        kwargs = plot_kwargs.copy()

        if cmap_name:
            kwargs["palette"] = cmap_name

        import seaborn as sns

        if axes_flipped:
            sns.kdeplot(data=df, y=data_col, hue=hue, ax=engine.current_ax, fill=True, **kwargs)
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)

            try:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, None, df[data_col])
            except Exception:
                pass
        else:
            sns.kdeplot(data=df, x=data_col, hue=hue, ax=engine.current_ax, fill=True, **kwargs)
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

            try:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[data_col], None)
            except Exception:
                pass

        return None