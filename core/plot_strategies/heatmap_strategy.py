from typing import TYPE_CHECKING, List, Dict, Any, Optional
import pandas as pd
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class HeatmapPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        x = x_col if x_col and x_col != "None" else None
        y = y_cols[0] if len(y_cols) > 0 else None
        z = y_cols[1] if len(y_cols) > 1 else None

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        cbar_kws = general_kwargs.pop("cbar_kws", {})
        kwargs = plot_kwargs.copy()

        if cmap_name:
            kwargs["cmap"] = cmap_name

        import seaborn as sns

        valid_x = x and x in df.columns
        valid_y = y and y in df.columns
        valid_z = z and z in df.columns

        if axes_flipped and valid_x and valid_y:
            x, y = y, x

        if valid_x and valid_y:
            if valid_z:
                plot_data = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
            else:
                plot_data = pd.crosstab(df[y], df[x])

            sns.heatmap(plot_data, annot=True, ax=engine.current_ax, cbar=False, picker=True, **kwargs)

            if xlabel is None:
                xlabel = x
            if ylabel is None:
                ylabel = y
        else:
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.empty:
                raise ValueError("No numeric columns available")

            plot_data = numeric_df.corr()
            sns.heatmap(plot_data, annot=True, ax=engine.current_ax, cbar=False, picker=True, **kwargs)

        if engine.current_ax.collections:
            cb = engine.current_figure.colorbar(engine.current_ax.collections[0], ax=engine.current_ax, **cbar_kws)
            engine.current_ax._cbar_obj = cb

        if axes_flipped and valid_x and valid_y:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)
            engine._helper_apply_flipped_labels(plot_tab, x, [y], font_family)
        elif axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        return None