from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class PiePlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        y_col = y_cols[0] if y_cols else x_col

        title = general_kwargs.pop('title', None)
        legend = general_kwargs.pop('legend', True)
        cmap_name = general_kwargs.pop('cmap', general_kwargs.pop('palette', None))

        show_percentages = plot_kwargs.pop("show_percentages", general_kwargs.pop("show_percentages", True))
        start_angle = plot_kwargs.pop("start_angle", general_kwargs.pop("start_angle", 0))
        explode_first = plot_kwargs.pop("explode_first", general_kwargs.pop("explode_first", False))
        explode_distance = plot_kwargs.pop("explode_distance", general_kwargs.pop("explode_distance", 0.1))
        shadow = plot_kwargs.pop("shadow", general_kwargs.pop("shadow", False))

        if hasattr(plot_tab, "pie_show_percentages_check"):
            show_percentages = plot_tab.pie_show_percentages_check.isChecked()
        if hasattr(plot_tab, "pie_start_angle_spin"):
            start_angle = plot_tab.pie_start_angle_spin.value()
        if hasattr(plot_tab, "pie_explode_check"):
            explode_first = plot_tab.pie_explode_check.isChecked()
        if hasattr(plot_tab, "pie_explode_distance_spin"):
            explode_distance = plot_tab.pie_explode_distance_spin.value()
        if hasattr(plot_tab, "pie_shadow_check"):
            shadow = plot_tab.pie_shadow_check.isChecked()

        is_donut_enabled = False
        if hasattr(plot_tab, "pie_donut_check"):
            is_donut_enabled = plot_tab.pie_donut_check.isChecked()

        kwargs = plot_kwargs.copy()

        if is_donut_enabled:
            donut_ring_width = 0.3
            if hasattr(plot_tab, "pie_donut_width_spin"):
                donut_ring_width = float(plot_tab.pie_donut_width_spin.value())
            current_wedgeprops = kwargs.get("wedgeprops", {})
            current_wedgeprops["width"] = donut_ring_width
            kwargs["wedgeprops"] = current_wedgeprops

        autopct = "%1.2f%%" if show_percentages else None

        explode = None
        if explode_first and not df[y_col].empty:
            explode = [explode_distance] + [0] * (len(df[y_col]) - 1)

        if cmap_name:
            colors = engine._get_colors_from_cmap(cmap_name, len(df[y_col]))
            if colors:
                kwargs["colors"] = colors

        engine.current_ax.pie(
            df[y_col],
            labels=df[x_col],
            autopct=autopct,
            startangle=start_angle,
            explode=explode,
            shadow=shadow,
            **kwargs
        )

        engine.current_ax.set_ylabel('')
        engine.current_ax.axis("equal")

        engine._set_labels(title, None, None, False, **general_kwargs)

        if legend:
            engine.current_ax.legend(loc="best")

        return None