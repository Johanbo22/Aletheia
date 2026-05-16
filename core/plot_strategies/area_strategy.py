from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class AreaPlotStrategy(BasePlotStrategy):
    
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop('cmap', None)
        secondary_y = general_kwargs.pop("secondary_y", None)
        secondary_plot_type = general_kwargs.pop("secondary_plot_type", "Line")

        kwargs = plot_kwargs.copy()

        if cmap_name:
            kwargs["cmap"] = cmap_name

        alpha_val = kwargs.pop("alpha", 0.7)
        if hasattr(plot_tab, "alpha_slider"):
            alpha_val = plot_tab.alpha_slider.value() / 100.0

        if axes_flipped:
            for col in y_cols:
                engine.current_ax.fill_betweenx(
                    df[x_col],
                    0,
                    df[col],
                    label=col,
                    alpha=alpha_val,
                    picker=5,
                    **kwargs
                )

            engine._helper_apply_flipped_labels(plot_tab, x_col, y_cols, font_family)
            if legend and len(y_cols) > 1:
                engine.current_ax.legend()

            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)

            try:
                y_data = df[y_cols[0]] if len(y_cols) == 1 else None
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, y_data, df[x_col])
            except Exception:
                pass
        else:
            kwargs["alpha"] = alpha_val
            df_plot = df[df[x_col].notna()].set_index(x_col)[y_cols]
            df_plot.plot(kind="area", ax=engine.current_ax, stacked=True, picker=True, **kwargs)

            ax2 = None
            if secondary_y:
                ax2 = engine._handle_secondary_axis(df, x_col, secondary_y, secondary_plot_type, **general_kwargs)

            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

            if legend:
                if ax2:
                    engine._consolidate_legends(engine.current_ax, ax2)
                else:
                    engine.current_ax.legend()

            try:
                y_data = df[y_cols[0]] if len(y_cols) == 1 else None
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], y_data)
            except Exception:
                pass

        return None