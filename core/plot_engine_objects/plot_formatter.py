"""
Handles axes formatting, labels, and datetime heuristics for the PlotEngine
"""

from typing import Any, List, Optional, TYPE_CHECKING

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

from ui.status_bar import LogLevel

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
    from core.plot_engine import PlotEngine

class PlotFormatter:
    """Manages axes formatting and labeling for PlotEngine"""

    def __init__(self, engine: "PlotEngine") -> None:
        self.engine = engine

    def set_labels(self, title: Optional[str], xlabel: Optional[str], ylabel: Optional[str], legend: bool,
                   **kwargs: Any) -> None:
        """Sets labels and handles LaTeX rendering if requested"""
        usetex = kwargs.get("usetext", False)
        plt.rcParams["text.usetex"] = usetex

        default_weight = "normal" if usetex else "bold"
        title_weight = kwargs.get("title_weight", default_weight)

        if title:
            self.engine.current_ax.set_title(title, fontsize=14, fontweight=title_weight, picker=True)
        if xlabel:
            self.engine.current_ax.set_xlabel(xlabel, fontsize=12, picker=True)
        if ylabel:
            self.engine.current_ax.set_ylabel(ylabel, fontsize=12, picker=True)

        zlabel = kwargs.get("zlabel", None)
        if zlabel and hasattr(self.engine.current_ax, "set_zlabel"):
            self.engine.current_ax.set_zlabel(zlabel, fontsize=12, picker=True)

        if legend:
            self.engine.current_ax.legend()

    def format_categorical_axis(self, axis: Any, labels: List[Any]) -> None:
        """
        Formats categorical axes with better
        tick spacing to prevent overcrowding
        """
        if labels is None or len(labels) == 0:
            return

        n_labels = len(labels)
        MAX_TICKS = 20

        if n_labels > MAX_TICKS:
            step = int(np.ceil(n_labels / MAX_TICKS))
            indices = np.arange(0, n_labels, step)
            subset_labels = [labels[i] for i in indices]

            axis.set_major_locator(ticker.FixedLocator(indices))
            axis.set_major_formatter(ticker.FixedFormatter(subset_labels))
        else:
            axis.set_major_locator(ticker.FixedLocator(np.arange(n_labels)))
            axis.set_major_formatter(ticker.FixedFormatter(labels))

        if axis == self.engine.current_ax.xaxis:
            plt.setp(self.engine.current_ax.get_xticklabels(), rotation=45, ha="right")

    def is_datetime_column(self, plot_tab: "PlotTab", data: Any) -> bool:
        """
        Checks if the provided data series is a datetime format
        """
        if data is None:
            return False

        try:
            if isinstance(data, pd.Series):
                if pd.api.types.is_datetime64_any_dtype(data):
                    return True
                if data.dtype == "object":
                    if data.empty:
                        return False

                    valid_samples = data.dropna().head(50)
                    if valid_samples.empty:
                        return False

                    try:
                        converted = pd.to_datetime(valid_samples, errors="coerce")
                        if converted.notna().mean() > 0.5:
                            return True
                    except Exception:
                        pass
            elif hasattr(data, "dtype"):
                return pd.api.types.is_datetime64_any_dtype(data.dtype)
        except Exception as error:
            plot_tab.status_bar.log(f"Datetime detection warning: {str(error)}", LogLevel.WARNING)
        return False

    def apply_auto_datetime_format(self, plot_tab: "PlotTab", axis: Any, data: Any) -> None:
        """Applies optimal datetime formatting based on the input data range."""
        if data is None or len(data) < 2 or not self.is_datetime_column(plot_tab, data):
            return

        try:
            if isinstance(data, pd.Series):
                if data.dtype == "object":
                    data = pd.to_datetime(data, utc=True, errors="coerce")

            data = data.dropna()

            if len(data) < 2:
                return

            date_range = data.max() - data.min()
            if date_range <= pd.Timedelta(hours=6):
                axis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
                axis.set_major_locator(mdates.MinuteLocator(interval=max(1, len(data) // 10)))
            elif date_range <= pd.Timedelta(days=1):
                axis.set_major_formatter(mdates.DateFormatter("%H:%M"))
                axis.set_major_locator(mdates.HourLocator(interval=max(1, len(data) // 12)))
            elif date_range <= pd.Timedelta(days=7):
                axis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
                axis.set_major_locator(mdates.DayLocator(interval=1))
            elif date_range <= pd.Timedelta(days=30):
                axis.set_major_formatter(mdates.DateFormatter("%m/%d"))
                axis.set_major_locator(mdates.DayLocator(interval=max(1, date_range.days // 10)))
            elif date_range <= pd.Timedelta(days=365):
                axis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                axis.set_major_locator(mdates.MonthLocator(interval=max(1, date_range.days // 90)))
            else:
                axis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                axis.set_major_locator(mdates.YearLocator())
        except Exception as error:
            plot_tab.status_bar.log(f"Failed to auto-format datetime: {str(error)}", LogLevel.WARNING)

    def set_intelligent_locator(self, plot_tab: "PlotTab", axis: Any, data: Any) -> None:
        """Sets tick locators based intelligently on the data range."""
        if data is None or len(data) < 2 or not self.is_datetime_column(plot_tab, data):
            return

        try:
            if isinstance(data, pd.Series):
                if data.dtype == "object":
                    data = pd.to_datetime(data, utc=True, errors="coerce")
            data = data.dropna()

            if len(data) < 2:
                return

            date_range = data.max() - data.min()
            if date_range <= pd.Timedelta(hours=6):
                axis.set_major_locator(mdates.MinuteLocator(interval=max(1, len(data) // 10)))
            elif date_range <= pd.Timedelta(days=1):
                axis.set_major_locator(mdates.HourLocator(interval=max(1, len(data) // 12)))
            elif date_range <= pd.Timedelta(days=7):
                axis.set_major_locator(mdates.DayLocator(interval=1))
            elif date_range <= pd.Timedelta(days=30):
                axis.set_major_locator(mdates.MonthLocator(interval=max(1, date_range.days // 10)))
            elif date_range <= pd.Timedelta(days=365):
                axis.set_major_locator(mdates.MonthLocator(interval=max(1, date_range.days // 90)))
            else:
                axis.set_major_locator(mdates.YearLocator())
        except Exception as error:
            plot_tab.status_bar.log(f"Failed to set datetime locator: {str(error)}", LogLevel.WARNING)

    def format_datetime_axis(self, plot_tab: "PlotTab", ax: Any, x_data: Any, y_data: Any = None) -> None:
        """Formats datetime axes using user overrides or intelligent auto-scaling."""
        is_x_datetime = self.is_datetime_column(plot_tab, x_data)
        is_y_datetime = self.is_datetime_column(plot_tab, y_data) if y_data is not None else False

        use_custom_format: bool = plot_tab.custom_datetime_check.isChecked()

        if is_x_datetime:
            try:
                if isinstance(x_data, pd.Series):
                    if x_data.dtype == "object":
                        x_data = pd.to_datetime(x_data, utc=True, errors="coerce")
                    elif not hasattr(x_data.dtype, "tz") or x_data.dtype.tz is None:
                        x_data = x_data.dt.tz_localize("UTC", nonexistent="shift_forward", ambiguous="infer")
            except Exception as error:
                plot_tab.status_bar.log(f"X-axis timezone handling: {str(error)}", LogLevel.WARNING)

            if use_custom_format:
                format_text = plot_tab.x_datetime_format_combo.currentText()

                if format_text == "Custom":
                    custom_format = plot_tab.x_custom_datetime_input.text().strip()
                    if custom_format:
                        try:
                            ax.xaxis.set_major_formatter(mdates.DateFormatter(custom_format))
                            self.set_intelligent_locator(plot_tab, ax.xaxis, x_data)
                        except Exception as error:
                            plot_tab.status_bar.log(f"Invalid datetime format: {str(error)}", LogLevel.WARNING)
                            self.apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
                    else:
                        self.apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
                elif format_text == "Auto":
                    self.apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
                else:
                    format_code = format_text.split(" ")[0]
                    try:
                        ax.xaxis.set_major_formatter(mdates.DateFormatter(format_code))
                        self.set_intelligent_locator(plot_tab, ax.xaxis, x_data)
                    except Exception as error:
                        plot_tab.status_bar.log(f"Invalid datetime format: {str(error)}", LogLevel.WARNING)
                        self.apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
            else:
                self.apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)

        if is_y_datetime:
            try:
                if isinstance(y_data, pd.Series):
                    if y_data.dtype == 'object':
                        y_data = pd.to_datetime(y_data, utc=True, errors='coerce')
                    elif not hasattr(y_data.dtype, 'tz') or y_data.dtype.tz is None:
                        y_data = y_data.dt.tz_localize('UTC', nonexistent='shift_forward', ambiguous='infer')
            except Exception as error:
                plot_tab.status_bar.log(f"Y-axis timezone handling: {str(error)}", LogLevel.WARNING)

            if use_custom_format:
                format_text = plot_tab.y_datetime_format_combo.currentText()

                if format_text == "Custom":
                    custom_format = plot_tab.y_custom_datetime_format_input.text().strip()
                    if custom_format:
                        try:
                            ax.yaxis.set_major_formatter(mdates.DateFormatter(custom_format))
                            self.set_intelligent_locator(plot_tab, ax.yaxis, y_data)
                        except Exception as error:
                            plot_tab.status_bar.log(f"Invalid datetime format: {str(error)}", LogLevel.WARNING)
                            self.apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
                    else:
                        self.apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
                elif x_data is not None and hasattr(x_data, "dtype") and (
                        x_data.dtype == "object" or isinstance(x_data.dtype, pd.CategoricalDtype)):
                    try:
                        labels = x_data.unique()
                        labels = [l for l in labels if pd.notna(l)]
                        self.format_categorical_axis(ax.xaxis, labels)
                    except Exception:
                        pass
                elif format_text == "Auto":
                    self.apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
                else:
                    format_code = format_text.split(" ")[0]
                    try:
                        ax.yaxis.set_major_formatter(mdates.DateFormatter(format_code))
                        self.set_intelligent_locator(plot_tab, ax.yaxis, y_data)
                    except Exception as error:
                        plot_tab.status_bar.log(f"Invalid datetime format: {str(error)}", LogLevel.WARNING)
                        self.apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
            else:
                self.apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)

    def apply_flipped_labels(self, plot_tab: "PlotTab", x_col: str, y_cols: List[str], font_family: str) -> None:
        """Correctly applies axes labels when horizontal/flipped representation is active."""
        if plot_tab.xlabel_check.isChecked():
            ylabel_to_use = plot_tab.xlabel_input.text() or x_col
            self.engine.current_ax.set_ylabel(
                ylabel_to_use,
                fontsize=plot_tab.xlabel_size_spin.value(),
                fontweight=plot_tab.xlabel_weight_combo.currentText(),
                fontfamily=font_family
            )

        if plot_tab.ylabel_check.isChecked():
            default_ylabel = y_cols[0] if len(y_cols) == 1 else ", ".join(y_cols)
            xlabel_to_use = plot_tab.ylabel_input.text() or default_ylabel
            self.engine.current_ax.set_xlabel(
                xlabel_to_use,
                fontsize=plot_tab.ylabel_size_spin.value(),
                fontweight=plot_tab.ylabel_weight_combo.currentText(),
                fontfamily=font_family
            )

        if plot_tab.title_check.isChecked():
            title_to_use = plot_tab.title_input.text() if plot_tab.title_input.text() else plot_tab.current_plot_type_name
            self.engine.current_ax.set_title(
                title_to_use,
                fontsize=plot_tab.title_size_spin.value(),
                fontweight=plot_tab.title_weight_combo.currentText(),
                fontfamily=font_family
            )
