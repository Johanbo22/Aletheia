from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_strategies.base_strategy import BasePlotStrategy

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class LinePlotStrategy(BasePlotStrategy):
    """Strategy for generating Line plots."""

    def execute(
        self,
        engine: 'PlotEngine',
        plot_tab: 'PlotTab',
        x_col: str,
        y_cols: List[str],
        axes_flipped: bool,
        font_family: str,
        plot_kwargs: Dict[str, Any],
        general_kwargs: Dict[str, Any]
    ) -> Optional[str]:

        df = plot_tab.data_handler.df
        engine._clear_axes()

        title = general_kwargs.pop("title", None)
        xlabel = general_kwargs.pop("xlabel", None)
        ylabel = general_kwargs.pop("ylabel", None)
        legend = general_kwargs.pop("legend", True)
        hue = general_kwargs.pop("hue", None)
        cmap_name = general_kwargs.pop("cmap", None)
        secondary_y = general_kwargs.pop("secondary_y", None)
        secondary_plot_type = general_kwargs.pop("secondary_plot_type", "Line")

        # Merge properties and filter invalid empty markers
        kwargs = plot_kwargs.copy()
        marker = kwargs.get("marker", None)
        if marker in (None, ""):
            kwargs.pop("marker", None)

        if axes_flipped:
            if hue:
                groups = df[hue].unique()
                colors = engine._get_colors_from_cmap(cmap_name, len(groups))

                for i, group in enumerate(groups):
                    mask = (df[hue] == group) & df[x_col].notna()
                    if colors: kwargs["color"] = colors[i]
                    for col in y_cols:
                        engine.current_ax.plot(
                            df.loc[mask, col], df.loc[mask, x_col],
                            label=f"{col} - {group}", picker=5, **kwargs
                        )
            else:
                colors = engine._get_colors_from_cmap(cmap_name, len(y_cols))
                for i, col in enumerate(y_cols):
                    mask = df[x_col].notna()
                    if colors: kwargs["color"] = colors[i]
                    engine.current_ax.plot(
                        df.loc[mask, col], df.loc[mask, x_col],
                        label=col, picker=5, **kwargs
                    )

            engine._helper_apply_flipped_labels(plot_tab, x_col, y_cols, font_family)
            if len(y_cols) > 1 or hue:
                engine.current_ax.legend()

            try:
                y_data = df[y_cols[0]] if len(y_cols) == 1 else None
                engine._helper_format_datetime_axis(
                    plot_tab, engine.current_ax, y_data, df[x_col]
                )
            except Exception:
                pass
        else:
            if hue:
                groups = df[hue].unique()
                colors = engine._get_colors_from_cmap(cmap_name, len(groups))

                for i, group in enumerate(groups):
                    mask = (df[hue] == group) & df[x_col].notna()
                    if colors: kwargs["color"] = colors[i]
                    for col in y_cols:
                        engine.current_ax.plot(
                            df.loc[mask, x_col], df.loc[mask, col],
                            label=f"{col} - {group}", picker=5, **kwargs
                        )
            else:
                colors = engine._get_colors_from_cmap(cmap_name, len(y_cols))
                for i, col in enumerate(y_cols):
                    mask = df[x_col].notna()
                    if colors: kwargs["color"] = colors[i]
                    engine.current_ax.plot(
                        df.loc[mask, x_col], df.loc[mask, col],
                        label=col, picker=5, **kwargs
                    )

            ax2 = None
            if secondary_y:
                ax2 = engine._handle_secondary_axis(
                    df, x_col, secondary_y, secondary_plot_type, **general_kwargs
                )

            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

            if legend:
                if ax2:
                    engine._consolidate_legends(engine.current_ax, ax2)
                else:
                    engine.current_ax.legend()

            try:
                y_data = df[y_cols[0]] if len(y_cols) == 1 else None
                engine._helper_format_datetime_axis(
                    plot_tab, engine.current_ax, df[x_col], y_data
                )
            except Exception:
                pass

        error_bar_type_str = plot_tab.error_bars_combo.currentText() if hasattr(plot_tab, "error_bars_combo") else "None"
        if error_bar_type_str != "None":
            engine.add_error_bars(df, x_col, y_cols, error_bar_type_str, axes_flipped, plot_tab=plot_tab)

        return None