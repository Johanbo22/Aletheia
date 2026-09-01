from typing import Any, Dict, List, TYPE_CHECKING

from src.core.plot_engine import PlotEngine
from src.core.plot_strategies.base_strategy import BasePlotStrategy
from src.ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from src.core.plot_engine import PlotEngine
    from src.ui.plot_tab import PlotTab

class EventplotPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if not y_cols:
            y_cols = [x_col] if x_col else []

        if not y_cols:
            return "No columns selected for eventplot."

        title = general_kwargs.pop("title", None)

        # Try to get xlabel from input safely as a fallback
        xlabel_input = ""
        if hasattr(plot_tab, "xlabel_input"):
            xlabel_input = plot_tab.xlabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "xlabel_input"):
            xlabel_input = plot_tab.view.xlabel_input.text()

        xlabel = general_kwargs.pop("xlabel", xlabel_input or "Value")
        ylabel = general_kwargs.pop("ylabel", None)
        legend = general_kwargs.pop("legend", None)

        kwargs = plot_kwargs.copy()
        kwargs["picker"] = kwargs.get("picker", True)

        # Eventplot default orientation is 'horizontal' (events along x-axis)
        orientation = "vertical" if axes_flipped else "horizontal"

        data_to_plot = [df[col].dropna().values for col in y_cols]
        num_series = len(data_to_plot)

        colors = kwargs.pop("colors", kwargs.pop("color", None))
        linestyles = kwargs.pop("linestyles", kwargs.pop("linestyle", "solid"))
        linewidths = kwargs.pop("linewidths", kwargs.pop("linewidth", None))
        alpha = kwargs.pop("alpha", 1.0)

        lineoffsets = kwargs.pop("lineoffsets", list(range(num_series)))
        linelengths = kwargs.pop("linelengths", 0.8 if num_series > 1 else 1.0)

        engine.current_ax.eventplot(
            data_to_plot,
            orientation=orientation,
            lineoffsets=lineoffsets,
            linelengths=linelengths,
            linewidths=linewidths,
            colors=colors,
            linestyles=linestyles,
            alpha=alpha,
            **kwargs
        )

        if num_series > 0:
            if axes_flipped:
                engine.current_ax.set_xticks(lineoffsets)
                engine.current_ax.set_xticklabels(y_cols)
            else:
                engine.current_ax.set_yticks(lineoffsets)
                engine.current_ax.set_yticklabels(y_cols)

        if axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, None, df[y_cols[0]])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_cols[0]], None)
        except Exception:
            pass

        return None