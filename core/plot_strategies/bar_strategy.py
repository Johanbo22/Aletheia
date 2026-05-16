from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class BarPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        df = df[df[x_col].notna()]
        engine._clear_axes()

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop("cmap", general_kwargs.pop("palette", None))
        secondary_y = general_kwargs.pop("secondary_y", None)
        secondary_plot_type = general_kwargs.pop("secondary_plot_type", "Line")

        width = plot_kwargs.pop("width", general_kwargs.pop("width", 0.8))
        if hasattr(plot_tab, "bar_width_spin"):
            width = plot_tab.bar_width_spin.value()

        kwargs = plot_kwargs.copy()

        if len(y_cols) == 1 and not hue:
            # Single Y column
            y_col_name = y_cols[0]
            if axes_flipped:
                engine.current_ax.barh(df[x_col], df[y_col_name], height=width, picker=True, **kwargs)
            else:
                engine.current_ax.bar(df[x_col], df[y_col_name], width=width, picker=True, **kwargs)

        elif len(y_cols) > 1:
            # Grouped bar chart natively in matplotlib
            x_labels = df[x_col].unique()
            x_pos = np.arange(len(x_labels))
            bar_width = width / len(y_cols)

            colors = engine._get_colors_from_cmap(cmap_name, len(y_cols))

            for i, col in enumerate(y_cols):
                offset = (i - len(y_cols) / 2) * bar_width + bar_width / 2
                values = []
                for label in x_labels:
                    mask = df[x_col] == label
                    if mask.any():
                        values.append(df.loc[mask, col].values[0])
                    else:
                        values.append(0)

                if colors: kwargs["color"] = colors[i]

                if axes_flipped:
                    engine.current_ax.barh(x_pos + offset, values, height=bar_width, label=col, picker=True, **kwargs)
                else:
                    engine.current_ax.bar(x_pos + offset, values, width=bar_width, label=col, picker=True, **kwargs)

            if axes_flipped:
                engine._helper_format_categorical_axis(engine.current_ax.yaxis, x_labels)
            else:
                engine._helper_format_categorical_axis(engine.current_ax.xaxis, x_labels)

        elif hue:
            # Single Y column with statistical hue using seaborn
            import seaborn as sns
            if cmap_name: kwargs["palette"] = cmap_name

            if axes_flipped:
                sns.barplot(data=df, y=x_col, x=y_cols[0], hue=hue, ax=engine.current_ax, orient="h", **kwargs)
            else:
                sns.barplot(data=df, x=x_col, y=y_cols[0], hue=hue, ax=engine.current_ax, **kwargs)

        ax2 = None
        if not axes_flipped and secondary_y:
            ax2 = engine._handle_secondary_axis(df, x_col, secondary_y, secondary_plot_type, horizontal=axes_flipped,
                                                **general_kwargs)

        if axes_flipped:
            engine._helper_apply_flipped_labels(plot_tab, x_col, y_cols, font_family)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        if legend:
            if ax2:
                engine._consolidate_legends(engine.current_ax, ax2)
            else:
                handles, labels = engine.current_ax.get_legend_handles_labels()
                if handles:
                    engine.current_ax.legend()

        try:
            if axes_flipped:
                y_data = df[y_cols[0]] if len(y_cols) == 1 else None
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, y_data, df[x_col])
            else:
                y_data = df[y_cols[0]] if len(y_cols) == 1 else None
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], y_data)
        except Exception:
            pass

        error_bar_type_str = plot_tab.error_bars_combo.currentText() if hasattr(plot_tab,
                                                                                "error_bars_combo") else "None"
        if error_bar_type_str != "None":
            engine.add_error_bars(df, x_col, y_cols, error_bar_type_str, axes_flipped, plot_tab=plot_tab)

        return None