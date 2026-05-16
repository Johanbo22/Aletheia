from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class StemPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log(f"Stem only supports one y column. Using: {y_cols[0]}", "WARNING")

        y_col = y_cols[0] if y_cols else x_col

        title = general_kwargs.pop("title", None)
        xlabel = general_kwargs.pop("xlabel", None)
        ylabel = general_kwargs.pop("ylabel", None)
        legend = general_kwargs.pop("legend", False)

        kwargs = plot_kwargs.copy()

        line_style = kwargs.pop("linestyle", "-")
        line_width = kwargs.pop("linewidth", 1.5)
        marker = kwargs.pop("marker", "o")

        marker_size = kwargs.pop("markersize", 6)
        if "s" in kwargs:
            marker_size = kwargs.pop("s")

        color = kwargs.pop("color", "#1f77b4")
        if "c" in kwargs:
            color = kwargs.pop("c")

        alpha = kwargs.pop("alpha", 1.0)
        label = kwargs.pop("label", str(y_col))
        bottom = kwargs.pop("bottom", 0)

        # Clean up orientation from kwargs just in case it leaks from general config
        kwargs.pop("orientation", None)

        if axes_flipped:
            markerline, stemlines, baseline = engine.current_ax.stem(
                df[y_col], df[x_col],
                orientation="horizontal",
                bottom=bottom,
                label=label,
                **kwargs
            )
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
            engine._set_labels(title, ylabel, xlabel, legend, **general_kwargs)
        else:
            markerline, stemlines, baseline = engine.current_ax.stem(
                df[x_col], df[y_col],
                orientation="vertical",
                bottom=bottom,
                label=label,
                **kwargs
            )
            engine._set_labels(title, xlabel, ylabel, legend, **general_kwargs)

        import matplotlib.pyplot as plt
        plt.setp(markerline, marker=marker, markersize=marker_size, color=color, alpha=alpha)
        plt.setp(stemlines, linestyle=line_style, linewidth=line_width, color=color, alpha=alpha)
        plt.setp(baseline, color="gray", linewidth=1, linestyle="-")

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_col], df[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], df[y_col])
        except Exception:
            pass

        return None