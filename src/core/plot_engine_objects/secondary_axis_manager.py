from typing import Any, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.core.plot_engine import PlotEngine

class SecondaryAxisManager:
    """
    Handles plotting data on a secondary axis
    TwinX and TwinY
    """

    def __init__(self, engine: "PlotEngine") -> None:
        self.engine = engine

    def handle_secondary_axis(self, df: pd.DataFrame, x: str, secondary_y: str, secondary_plot_type: str, **kwargs: Any) -> Any:
        """Plots data on a secondary y-axis (TwinX) or secondary x-axis (TwinY)"""
        if not secondary_y or secondary_y not in df.columns or not self.engine.current_ax:
            return None

        horizontal = kwargs.get("horizontal", False)
        label_str = f"{secondary_y} (Secondary)"

        if horizontal:
            ax2 = self.engine.current_ax.twiny()
            self.engine.secondary_ax = ax2

            if secondary_plot_type == "Line":
                ax2.plot(df[secondary_y], df[x], label=label_str)
            elif secondary_plot_type == "Bar":
                ax2.barh(df[x], df[secondary_y], label=label_str)
            elif secondary_plot_type == "Scatter":
                ax2.scatter(df[secondary_y], df[x], label=label_str)
            elif secondary_plot_type == "Area":
                ax2.fill_between(df[x], 0, df[secondary_y], label=label_str)
            else:
                ax2.plot(df[secondary_y], df[x], label=label_str)

            ax2.set_xlabel(secondary_y)
            ax2.tick_params(axis="x")
        else:
            ax2 = self.engine.current_ax.twinx()
            self.engine.secondary_ax = ax2

            if secondary_plot_type == "Line":
                ax2.plot(df[x], df[secondary_y], label=label_str)
            elif secondary_plot_type == "Bar":
                ax2.bar(df[x], df[secondary_y], label=label_str)
            elif secondary_plot_type == "Scatter":
                ax2.scatter(df[x], df[secondary_y], label=label_str)
            elif secondary_plot_type == "Area":
                ax2.fill_between(df[x], 0, df[secondary_y], label=label_str)
            else:
                ax2.plot(df[x], df[secondary_y], label=label_str)

            ax2.set_ylabel(secondary_y)
            ax2.tick_params(axis="y")

        return ax2

    def consolidate_legends(self, ax1: Any, ax2: Any) -> None:
        """Combine legends from primary and secondary axes into one."""
        if not ax1 and ax2:
            return

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()

        if lines1 or lines2:
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")