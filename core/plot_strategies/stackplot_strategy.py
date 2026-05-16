from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class StackPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) < 2:
            return "Stackplot requires at least two Y columns."

        title = general_kwargs.pop("title", None)
        xlabel = general_kwargs.pop("xlabel", None)
        ylabel = general_kwargs.pop("ylabel", None)
        legend = general_kwargs.pop("legend", True)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        kwargs = plot_kwargs.copy()

        df_sorted = df[df[x_col].notna()].sort_values(by=x_col)
        y_data = [df_sorted[col] for col in y_cols]

        if cmap_name:
            colors = engine._get_colors_from_cmap(cmap_name, len(y_cols))
            if colors:
                kwargs["colors"] = colors

        kwargs["picker"] = kwargs.get("picker", True)

        engine.current_ax.stackplot(df_sorted[x_col], *y_data, labels=y_cols, **kwargs)

        if axes_flipped:
            engine._helper_apply_flipped_labels(plot_tab, x_col, y_cols, font_family)
            engine._set_labels(title, ylabel, xlabel, legend, **general_kwargs)
        else:
            engine._set_labels(title, xlabel, ylabel, legend, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, None, df_sorted[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df_sorted[x_col], None)
        except Exception:
            pass

        return None