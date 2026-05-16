from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab
    
class ScatterPlotStrategy(BasePlotStrategy):
    
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            plot_tab.status_bar.log(f"Scatter only supports one y column. Using: {y_cols[0]}", "WARNING")

        y_col = y_cols[0]

        title = general_kwargs.pop('title', None)
        xlabel = general_kwargs.pop('xlabel', None)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        hue = general_kwargs.pop('hue', None)
        cmap_name = general_kwargs.pop("cmap", None)
        secondary_y = general_kwargs.pop("secondary_y", None)
        secondary_plot_type = general_kwargs.pop("secondary_plot_type", "Line")

        size_col = plot_kwargs.pop("size", general_kwargs.pop("size", None))
        size_min = plot_kwargs.pop("size_min", general_kwargs.pop("size_min", 30))
        size_max = plot_kwargs.pop("size_max", general_kwargs.pop("size_max", 500))

        s_min_global, s_max_global = 0.0, 0.0
        if size_col and size_col in df.columns:
            s_min_global, s_max_global = df[size_col].min(), df[size_col].max()

        kwargs = plot_kwargs.copy()

        real_x = y_col if axes_flipped else x_col
        real_y = x_col if axes_flipped else y_col

        if hue:
            groups = df[hue].unique()
            colors = engine._get_colors_from_cmap(cmap_name, len(groups))

            for i, group in enumerate(groups):
                mask = (df[hue] == group) & df[real_x].notna() & df[real_y].notna()
                if colors: kwargs["color"] = colors[i]

                if size_col and size_col in df.columns:
                    s_data = df.loc[mask, size_col]
                    if s_min_global == s_max_global or pd.isna(s_min_global):
                        kwargs["s"] = size_min
                    else:
                        kwargs["s"] = size_min + (size_max - size_min) * (s_data - s_min_global) / (
                                    s_max_global - s_min_global)

                engine.current_ax.scatter(df.loc[mask, real_x], df.loc[mask, real_y], label=str(group), picker=5,
                                          **kwargs)
        else:
            if cmap_name: kwargs["cmap"] = cmap_name
            mask = df[real_x].notna() & df[real_y].notna()

            if size_col and size_col in df.columns:
                s_data = df.loc[mask, size_col]
                if s_min_global == s_max_global or pd.isna(s_min_global):
                    kwargs["s"] = size_min
                else:
                    kwargs["s"] = size_min + (size_max - size_min) * (s_data - s_min_global) / (
                                s_max_global - s_min_global)

            engine.current_ax.scatter(df.loc[mask, real_x], df.loc[mask, real_y], picker=5, **kwargs)

        ax2 = None
        if not axes_flipped and secondary_y:
            ax2 = engine._handle_secondary_axis(df, x_col, secondary_y, secondary_plot_type, **general_kwargs)

        if axes_flipped:
            engine._helper_apply_flipped_labels(plot_tab, x_col, [y_col], font_family)
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        if legend:
            if ax2:
                engine._consolidate_legends(engine.current_ax, ax2)
            else:
                handles, labels = engine.current_ax.get_legend_handles_labels()

                if size_col and size_col in df.columns and s_min_global != s_max_global:
                    if not labels:
                        labels = []

                    labels.append(f"{size_col} (Size)")
                    handles.append(engine.current_ax.scatter([], [], s=0, color='none'))

                    for val in np.linspace(s_min_global, s_max_global, 4):
                        marker_size = size_min + (size_max - size_min) * (val - s_min_global) / (
                                    s_max_global - s_min_global)
                        dummy = engine.current_ax.scatter([], [], s=marker_size, color='gray', alpha=0.5)

                        handles.append(dummy)
                        labels.append(f"{int(val)}" if float(val).is_integer() else f"{val:.2f}")

                if handles:
                    engine.current_ax.legend(handles, labels)
                elif hue:
                    engine.current_ax.legend()

        try:
            if axes_flipped:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[y_col], df[x_col])
            else:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[x_col], df[y_col])
        except Exception:
            pass

        error_bar_type_str = plot_tab.error_bars_combo.currentText() if hasattr(plot_tab,
                                                                                "error_bars_combo") else "None"
        if error_bar_type_str != "None":
            engine.add_error_bars(df, x_col, [y_col], error_bar_type_str, axes_flipped, plot_tab=plot_tab)

        view = plot_tab.view
        if (view.regression_line_check.isChecked() or view.show_r2_check.isChecked() or
                view.show_rmse_check.isChecked() or view.show_equation_check.isChecked()):

            if axes_flipped:
                engine._helper_add_regression_analysis(plot_tab, y_col, x_col, flipped=True)
            else:
                engine._helper_add_regression_analysis(plot_tab, x_col, y_col, flipped=False)

        return None