import pandas as pd
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine

class PlotTableRenderer:
    """
    Handles rendering data tables directly onto the Matplotlib plot area
    """

    def __init__(self, engine: "PlotEngine") -> None:
        self.engine = engine

    def add_table(self, df: pd.DataFrame, loc: str = 'bottom', auto_font_size: bool = False, fontsize: int = 10,
                  scale_factor: float = 1.2, **kwargs: Any) -> None:
        """Renders a pandas DataFrame as a table on the plot."""
        if df is None or df.empty or not self.engine.current_ax:
            return

        for table in list(self.engine.current_ax.tables):
            table.remove()

        clean_kwargs = {k: v for k, v in kwargs.items() if k not in ["xlabel", "ylabel", "title", "legend"]}

        table_object = pd.plotting.table(
            self.engine.current_ax,
            df,
            loc=loc,
            **clean_kwargs
        )

        table_object.auto_set_font_size(auto_font_size)
        if not auto_font_size:
            table_object.set_fontsize(fontsize)
        table_object.scale(scale_factor, scale_factor)