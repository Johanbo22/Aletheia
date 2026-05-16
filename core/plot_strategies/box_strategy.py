from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab
    
class BoxPlotStrategy(BasePlotStrategy):
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

        if hue and hue in df.columns:
            import seaborn as sns
            if cmap_name:
                kwargs["palette"] = cmap_name

            if len(y_cols) == 1:
                if axes_flipped:
                    sns.boxplot(data=df, x=y_cols[0], y=hue, ax=engine.current_ax, orient="h", **kwargs)
                else:
                    sns.boxplot(data=df, x=hue, y=y_cols[0], ax=engine.current_ax, **kwargs)
            else:
                melted_df = df.melt(id_vars=[hue], value_vars=y_cols, var_name="Variable", value_name="Value")
                if axes_flipped:
                    sns.boxplot(data=melted_df, x="Value", y="Variable", hue=hue, ax=engine.current_ax, orient="h",
                                **kwargs)
                else:
                    sns.boxplot(data=melted_df, x="Variable", y="Value", hue=hue, ax=engine.current_ax, **kwargs)
        else:
            kwargs.pop("palette", None)

            if axes_flipped:
                df[y_cols].plot(kind="box", ax=engine.current_ax, vert=False, **kwargs)
            else:
                df[y_cols].plot(kind="box", ax=engine.current_ax, vert=True, **kwargs)

        if axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x_col, y_cols, font_family)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        return None