from typing import Any, Dict, List, TYPE_CHECKING

from src.core.plot_engine import PlotEngine
from src.core.plot_strategies.base_strategy import BasePlotStrategy
from src.ui.plot_tab import PlotTab
from src.ui.status_bar import LogLevel

if TYPE_CHECKING:
    from src.core.plot_engine import PlotEngine
    from src.ui.plot_tab import PlotTab

class ECDFPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool,
                font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        if len(y_cols) > 1:
            plot_tab.status_bar.log(f"ECDF only supports one y column. Using: {y_cols[0]}", LogLevel.WARNING)
        y_col = y_cols[0]
        general_kwargs["xlabel"] = plot_tab.view.xlabel_input.text() or y_col

        plot_method = getattr(engine, engine.AVAILABLE_PLOTS["ECDF"])
        plot_method(plot_tab.data_handler.df, y_col, **general_kwargs)
        try:
            engine._helper_format_datetime_axis(plot_tab, engine.current_ax, plot_tab.data_handler.df[y_col])
        except:
            pass
        return None
