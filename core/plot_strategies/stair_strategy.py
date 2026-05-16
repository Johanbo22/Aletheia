from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class StairsPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(f"Stairs only supports one y column. Using: {y_cols[0]}", "WARNING")

        y_col = y_cols[0] if y_cols else x_col

        title = general_kwargs.pop("title", None)
        xlabel = general_kwargs.pop("xlabel", None)
        ylabel = general_kwargs.pop("ylabel", None)
        legend = general_kwargs.pop("legend", True)
        cmap = general_kwargs.pop("cmap", None)

        kwargs = plot_kwargs.copy()

        kwargs["picker"] = kwargs.get("picker", True)
        where = kwargs.pop("where", "mid")

        df_sorted = df[df[x_col].notna()].sort_values(by=x_col)

        if axes_flipped:
            engine.current_ax.step(df_sorted[y_col], df_sorted[x_col], where=where, **kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
        else:
            engine.current_ax.step(df_sorted[x_col], df_sorted[y_col], where=where, **kwargs)
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df_sorted[y_col], df_sorted[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df_sorted[x_col], df_sorted[y_col])
        except Exception:
            pass

        return None