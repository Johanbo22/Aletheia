"""
Handles rendering of regression lines, error bars, and analytics for the PlotEngine.
"""

import pandas as pd
import numpy as np
from typing import TYPE_CHECKING, Any, List

from core.regression_analyser import RegressionMetrics, RegressionType, RegressionAnalyser, ErrorBarType
from ui.status_bar import LogLevel
from core.logger import Logger

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
    from core.plot_engine import PlotEngine

class PlotAnalyticsRenderer:
    """Renders statistical and analytical overlays atop the standard axes."""

    def __init__(self, engine: 'PlotEngine') -> None:
        self.engine = engine

    def add_regression_analysis(self, plot_tab: "PlotTab", x_col: str, y_col: str, flipped: bool = False) -> None:
        """Orchestrates regression calculation and renders analytical overlays."""
        try:
            reg_type_str = plot_tab.view.regression_type_combo.currentText() if hasattr(plot_tab,
                                                                                        "regression_type_combo") else "Linear"
            try:
                reg_type = RegressionType(reg_type_str)
            except ValueError:
                reg_type = RegressionType.LINEAR

            try:
                x_data, y_data = RegressionAnalyser.clean_data(plot_tab.data_handler.df, x_col, y_col, reg_type)
            except TypeError as error:
                plot_tab.status_bar.log(f"Regression skipped: {str(error)}", LogLevel.INFO)
                return

            if len(x_data) < 2:
                plot_tab.status_bar.log("Not enough data points to perform regression analysis", LogLevel.WARNING)
                return

            degree = plot_tab.view.poly_degree_spin.value() if hasattr(plot_tab, "poly_degree_spin") else 2
            try:
                result = RegressionAnalyser.compute_fit(x_data, y_data, reg_type, degree)
            except RuntimeError:
                plot_tab.status_bar.log(f"{reg_type.value} fit failed to converge", LogLevel.ERROR)
                return

            if plot_tab.view.regression_line_check.isChecked():
                self.render_regression_line(result.x_line, result.y_line, reg_type, flipped)

            if plot_tab.view.confidence_interval_check.isChecked():
                confidence = plot_tab.view.confidence_level_spin.value() / 100.0
                margin = RegressionAnalyser.compute_confidence_interval(x_data, result.residuals, result.x_line,
                                                                        confidence)
                self.render_confidence_interval(result.x_line, result.y_line, margin, confidence, flipped)

            self.render_regression_statistics(plot_tab, result.metrics, flipped)

            plot_tab.status_bar.log(
                f"Regression ({reg_type.value}): R²={result.metrics.r_squared:.4f}, RMSE={result.metrics.rmse:.4f}",
                LogLevel.SUCCESS
            )
        except Exception as error:
            plot_tab.status_bar.log(f"Regression analysis failed: {str(error)}", LogLevel.ERROR)
            import traceback
            logger = Logger.get_instance()
            logger.error(f"Regression error: {traceback.print_exc()}")

    def render_regression_line(self, x_line: np.ndarray, y_line: np.ndarray, reg_type: Any, flipped: bool) -> None:
        plot_args = (x_line, y_line) if not flipped else (y_line, x_line)
        reg_line = self.engine.current_ax.plot(
            *plot_args, color="red", linestyle="-", linewidth=2,
            label=f"{reg_type.value} Fit", alpha=0.5
        )[0]
        reg_line.set_gid("regression_line")

    def render_confidence_interval(self, x_line: np.ndarray, y_line: np.ndarray, margin: np.ndarray, confidence: float,
                                   flipped: bool) -> None:
        fill_args = (x_line, y_line - margin, y_line + margin) if not flipped else (
        y_line - margin, y_line + margin, x_line)
        if not flipped:
            ci_poly = self.engine.current_ax.fill_between(
                fill_args[0], fill_args[1], fill_args[2],
                color="red", alpha=0.15, label=f"{int(confidence * 100)}% CI", zorder=-1
            )
        else:
            ci_poly = self.engine.current_ax.fill_betweenx(
                fill_args[2], fill_args[0], fill_args[1],
                color="red", alpha=0.15, label=f"{int(confidence * 100)}% CI", zorder=-1
            )
        ci_poly.set_gid("confidence_interval")

    def render_regression_statistics(self, plot_tab: 'PlotTab', metrics: RegressionMetrics, flipped: bool) -> None:
        stats_text = []
        eq_x_label = "y" if flipped else "x"
        eq_y_label = "x" if flipped else "y"

        if plot_tab.view.show_equation_check.isChecked():
            formatted_eq = metrics.equation_str.replace('x', eq_x_label)
            stats_text.append(f'{eq_y_label} = {formatted_eq}')

        if plot_tab.view.show_r2_check.isChecked():
            stats_text.append(f"R² = {metrics.r_squared:.4f}")

        if plot_tab.view.show_rmse_check.isChecked():
            stats_text.append(f"RMSE = {metrics.rmse:.4f}")

        if stats_text:
            textstr = "\n".join(stats_text)
            props = dict(boxstyle="round", facecolor="wheat", alpha=0.85, edgecolor="black", linewidth=1)
            font_family = plot_tab.view.font_family_combo.currentFont().family()
            self.engine.current_ax.text(
                0.05, 0.95, textstr, transform=self.engine.current_ax.transAxes,
                fontsize=11, verticalalignment='top', bbox=props,
                fontfamily=font_family, zorder=15
            )

    def add_error_bars(self, df: pd.DataFrame, x_col: str, y_cols: List[str], error_bar_type_str: str,
                       flipped: bool = False, plot_tab: "PlotTab" = None) -> None:
        """Computes standard deviation and standard error bars across series."""
        try:
            error_bar_type = ErrorBarType(error_bar_type_str)
        except ValueError:
            error_bar_type = ErrorBarType.NONE

        if error_bar_type == ErrorBarType.NONE:
            return

        ecolor = "black"
        elinewidth = 1.5
        capsize = 4.0
        alpha = 0.5
        zorder = 10

        if plot_tab is not None:
            if hasattr(plot_tab, "error_bar_color"):
                ecolor = plot_tab.error_bar_color
            if hasattr(plot_tab, "view") and plot_tab.view is not None:
                if hasattr(plot_tab.view, "error_bar_linewidth_spin"):
                    elinewidth = plot_tab.view.error_bar_linewidth_spin.value()
                if hasattr(plot_tab.view, "error_bar_capsize_spin"):
                    capsize = plot_tab.view.error_bar_capsize_spin.value()
                if hasattr(plot_tab.view, "error_bar_alpha_slider"):
                    alpha = plot_tab.view.error_bar_alpha_slider.value() / 100.0
                if hasattr(plot_tab.view, "error_bar_zorder_spin"):
                    zorder = plot_tab.view.error_bar_zorder_spin.value()

        for y_col in y_cols:
            clean_df = df[[x_col, y_col]].dropna()
            if clean_df.empty:
                continue

            grouped = clean_df.groupby(x_col)[y_col]
            x_centers = grouped.mean().index.to_numpy()
            y_centers = grouped.mean().to_numpy(dtype=float)

            if error_bar_type == ErrorBarType.STANDARD_DEVIATION:
                errors = grouped.std().fillna(0).to_numpy(dtype=float)
            elif error_bar_type == ErrorBarType.STANDARD_ERROR:
                errors = grouped.sem().fillna(0).to_numpy(dtype=float)
            else:
                continue

            if np.all(errors == 0):
                x_centers = clean_df[x_col].to_numpy()
                y_centers = clean_df[y_col].to_numpy(dtype=float)

                if error_bar_type == ErrorBarType.STANDARD_DEVIATION:
                    global_err = clean_df[y_col].std()
                else:
                    global_err = clean_df[y_col].sem()

                if pd.isna(global_err) or global_err == 0:
                    continue

                errors = np.full(len(y_centers), global_err)

            err_args = (x_centers, y_centers) if not flipped else (y_centers, x_centers)
            err_kwargs = {"yerr": errors} if not flipped else {"xerr": errors}

            data_line, caplines, barcols = self.engine.current_ax.errorbar(
                *err_args, **err_kwargs,
                fmt="none", ecolor=ecolor, alpha=alpha,
                capsize=capsize, zorder=zorder, elinewidth=elinewidth
            )
            if data_line is not None:
                data_line.set_gid("error_bar")

            if caplines is not None:
                for cap in caplines:
                    if cap is not None:
                        cap.set_linestyle('none')
                        cap.set_gid("error_bar")

            if barcols is not None:
                for col in barcols:
                    if col is not None:
                        col.set_gid("error_bar")