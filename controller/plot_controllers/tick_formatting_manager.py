from typing import Any, Optional, TYPE_CHECKING

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, FuncFormatter, MaxNLocator, NullLocator

from ui.status_bar import LogLevel

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class TickFormattingManager:
    """Manages tick locators, formatters, and parameters for plot axes."""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab

    def apply_initial_locators(self) -> None:
        """Applies initial MaxNLocator constraints based on UI settings."""
        ax = self.plot_tab.plot_engine.current_ax
        if not ax:
            return

        try:
            allowed_locators = ["AutoLocator", "MaxNLocator", "LinearLocator", "MultipleLocator"]
            x_locator_name = type(ax.xaxis.get_major_locator()).__name__
            if x_locator_name in allowed_locators:
                ax.xaxis.set_major_locator(
                    MaxNLocator(nbins=self.plot_tab.view.x_max_ticks_spin.value()))

            y_locator_name = type(ax.yaxis.get_major_locator()).__name__
            if y_locator_name in allowed_locators:
                ax.yaxis.set_major_locator(
                    MaxNLocator(nbins=self.plot_tab.view.y_max_ticks_spin.value()))

            if hasattr(ax, "zaxis"):
                z_locator_name = type(ax.zaxis.get_major_locator()).__name__
                if z_locator_name in allowed_locators:
                    ax.zaxis.set_major_locator(
                        MaxNLocator(nbins=self.plot_tab.view.z_max_ticks_spin.value()))
        except Exception as e:
            self.plot_tab.status_bar.log(f"Could not apply initial tick locators: {str(e)}", LogLevel.WARNING)

    def apply_tick_customization(self) -> None:
        """Apply tick label formatting, rotations, units, and locators."""
        if not self.plot_tab.plot_engine.current_ax:
            return
        self._apply_major_tick_params()
        self._setup_minor_tick_locators()
        self._apply_minor_tick_params()
        self._apply_axis_formatters()
        self._apply_axis_rotations_and_inversions()

    def _apply_major_tick_params(self) -> None:
        """Configure parameters for major ticks on the current plot axes."""
        ax = self.plot_tab.plot_engine.current_ax
        ax.tick_params(
            axis="x", labelsize=self.plot_tab.view.xtick_label_size_spin.value(),
            direction=self.plot_tab.view.x_major_tick_direction_combo.currentText(),
            width=self.plot_tab.view.x_major_tick_width_spin.value(), which="major"
        )
        ax.tick_params(
            axis="y", labelsize=self.plot_tab.view.ytick_label_size_spin.value(),
            direction=self.plot_tab.view.y_major_tick_direction_combo.currentText(),
            width=self.plot_tab.view.y_major_tick_width_spin.value(), which="major"
        )

        if hasattr(ax, "zaxis"):
            ax.tick_params(
                axis="z", labelsize=self.plot_tab.view.ztick_label_size_spin.value(),
                direction=self.plot_tab.view.z_major_tick_direction_combo.currentText(),
                width=self.plot_tab.view.z_major_tick_width_spin.value(), which="major"
            )

        if self.plot_tab.view.x_top_axis_check.isChecked():
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position("top")
        else:
            ax.xaxis.tick_bottom()
            ax.xaxis.set_label_position("bottom")

    def _setup_minor_tick_locators(self) -> None:
        """Setup visibility and locators for minor ticks based on grid/tick settings."""
        ax = self.plot_tab.plot_engine.current_ax
        needs_x_minor = self.plot_tab.view.x_show_minor_ticks_check.isChecked()
        needs_y_minor = self.plot_tab.view.y_show_minor_ticks_check.isChecked()
        needs_z_minor = hasattr(self.plot_tab.view,
                                "z_show_minor_ticks_check") and self.plot_tab.view.z_show_minor_ticks_check.isChecked()

        if self.plot_tab.view.grid_check.isChecked():
            if self.plot_tab.view.independent_grid_check.isChecked():
                if self.plot_tab.view.x_minor_grid_check.isChecked():
                    needs_x_minor = True
                if self.plot_tab.view.y_minor_grid_check.isChecked():
                    needs_y_minor = True
            else:
                which = self.plot_tab.view.grid_which_type_combo.currentText()
                axis = self.plot_tab.view.grid_axis_combo.currentText()
                if which in ["minor", "both"]:
                    if axis in ["x", "both"]:
                        needs_x_minor = True
                    if axis in ["y", "both"]:
                        needs_y_minor = True
                    if hasattr(ax, "zaxis") and axis == "both":
                        needs_z_minor = True

        try:
            self._set_minor_locator(ax.xaxis, needs_x_minor)
            self._set_minor_locator(ax.yaxis, needs_y_minor)
            if hasattr(ax, "zaxis"):
                self._set_minor_locator(ax.zaxis, needs_z_minor)
        except Exception as e:
            self.plot_tab.status_bar.log(f"Warning mapping minor locators: {str(e)}", LogLevel.WARNING)

    def _set_minor_locator(self, axis_obj: Any, needs_minor: bool) -> None:
        """Helper to set AutoMinorLocator or NullLocator based on state."""
        if needs_minor:
            locator_name = type(axis_obj.get_major_locator()).__name__
            if locator_name in ["AutoLocator", "MaxNLocator"]:
                axis_obj.set_minor_locator(AutoMinorLocator())
        else:
            axis_obj.set_minor_locator(NullLocator())

    def _apply_minor_tick_params(self) -> None:
        """Configure visual parameters for minor ticks."""
        ax = self.plot_tab.plot_engine.current_ax
        if self.plot_tab.view.x_show_minor_ticks_check.isChecked():
            ax.tick_params(
                axis="x", which="minor", bottom=True, top=self.plot_tab.view.x_top_axis_check.isChecked(),
                direction=self.plot_tab.view.x_minor_tick_direction_combo.currentText(),
                width=self.plot_tab.view.x_minor_tick_width_spin.value()
            )
        else:
            ax.tick_params(axis="x", which="minor", bottom=False, top=False)

        if self.plot_tab.view.y_show_minor_ticks_check.isChecked():
            ax.tick_params(
                axis="y", which="minor", left=True, right=False,
                direction=self.plot_tab.view.y_minor_tick_direction_combo.currentText(),
                width=self.plot_tab.view.y_minor_tick_width_spin.value()
            )
        else:
            ax.tick_params(axis="y", which="minor", left=False, right=False)

        if hasattr(ax, "zaxis") and hasattr(self.plot_tab.view, "z_show_minor_ticks_check"):
            if self.plot_tab.view.z_show_minor_ticks_check.isChecked():
                ax.tick_params(
                    axis="z", which="minor", direction=self.plot_tab.view.z_minor_tick_direction_combo.currentText(),
                    width=self.plot_tab.view.z_minor_tick_width_spin.value()
                )
            else:
                ax.tick_params(axis="z", which="minor")

    def _apply_axis_formatters(self) -> None:
        """Apply custom display units or datetime formatters to axes."""
        ax = self.plot_tab.plot_engine.current_ax
        try:
            x_unit_str = self.plot_tab.view.x_display_units_combo.currentText()
            if x_unit_str != "None":
                x_formatter = self.create_axis_formatter(x_unit_str)
                if x_formatter:
                    ax.xaxis.set_major_formatter(x_formatter)

            y_unit_str = self.plot_tab.view.y_display_units_combo.currentText()
            if y_unit_str != "None":
                y_formatter = self.create_axis_formatter(y_unit_str)
                if y_formatter:
                    ax.yaxis.set_major_formatter(y_formatter)

            if hasattr(ax, "zaxis") and hasattr(self.plot_tab.view, "z_display_units_combo"):
                z_unit_str = self.plot_tab.view.z_display_units_combo.currentText()
                if z_unit_str != "None":
                    z_formatter = self.create_axis_formatter(z_unit_str)
                    if z_formatter:
                        ax.zaxis.set_major_formatter(z_formatter)
        except Exception as e:
            self.plot_tab.status_bar.log(f"Failed to apply display units: {str(e)}", LogLevel.ERROR)

        if self.plot_tab.view.custom_datetime_check.isChecked():
            self._apply_datetime_formatters()

    def _apply_datetime_formatters(self) -> None:
        """Apply datetime formatters to x and y axes if configured."""
        format_map = {
            "YYYY-MM-DD" : "%Y-%m-%d", "MM/DD/YYYY": "%m/%d/%Y", "DD/MM/YYYY": "%d/%m/%Y",
            "YYYY/MM/DD" : "%Y/%m/%d", "DD-MM-YYYY": "%d-%m-%Y", "Mon DD, YYYY": "%b %d, %Y",
            "DD Mon YYYY": "%d %b %Y", "YYYY-MM": "%Y-%m", "MM-YYYY": "%m-%Y",
            "HH:MM:SS"   : "%H:%M:%S", "YYYY-MM-DD HH:MM": "%Y-%m-%d %H:%M"
        }
        ax = self.plot_tab.plot_engine.current_ax

        x_fmt_name = self.plot_tab.view.x_datetime_format_combo.currentText()
        if x_fmt_name and x_fmt_name != "None":
            fmt_str = self.plot_tab.view.x_custom_datetime_input.text() if x_fmt_name == "Custom" else format_map.get(
                x_fmt_name)
            if fmt_str:
                try:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt_str))
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=15))
                except Exception as error:
                    self.plot_tab.status_bar.log(f"Failed to apply X-axis datetime format: {str(error)}",
                                                 LogLevel.ERROR)

        y_fmt_name = self.plot_tab.view.y_datetime_format_combo.currentText()
        if y_fmt_name and y_fmt_name != "None":
            fmt_str = self.plot_tab.view.y_custom_datetime_format_input.text() if y_fmt_name == "Custom" else format_map.get(
                y_fmt_name)
            if fmt_str:
                try:
                    ax.yaxis.set_major_formatter(mdates.DateFormatter(fmt_str))
                    ax.yaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=15))
                except Exception as error:
                    self.plot_tab.status_bar.log(f"Failed to apply Y-axis datetime format: {str(error)}",
                                                 LogLevel.ERROR)

    def _apply_axis_rotations_and_inversions(self) -> None:
        """Apply tick label rotations and axis orientation inversion."""
        ax = self.plot_tab.plot_engine.current_ax
        plt.setp(ax.get_xticklabels(), rotation=self.plot_tab.view.xtick_rotation_spin.value())
        plt.setp(ax.get_yticklabels(), rotation=self.plot_tab.view.ytick_rotation_spin.value())
        if hasattr(ax, "zaxis"):
            plt.setp(ax.get_zticklabels(), rotation=self.plot_tab.view.ztick_rotation_spin.value())

        if self.plot_tab.view.x_invert_axis_check.isChecked():
            if not ax.xaxis_inverted():
                ax.invert_xaxis()
        else:
            if ax.xaxis_inverted():
                ax.invert_xaxis()

        if self.plot_tab.view.y_invert_axis_check.isChecked():
            if not ax.yaxis_inverted():
                ax.invert_yaxis()
        else:
            if ax.yaxis_inverted():
                ax.invert_yaxis()

        if hasattr(ax, "zaxis"):
            if self.plot_tab.view.z_invert_axis_check.isChecked():
                if not ax.zaxis_inverted():
                    ax.invert_zaxis()
            else:
                if ax.zaxis_inverted():
                    ax.invert_zaxis()

    def create_axis_formatter(self, unit_str: str) -> Optional[FuncFormatter]:
        """Create a matplotlib FuncFormatter based on the selected unit."""
        if unit_str == "None" or not unit_str:
            return None

        formatters = {
            "Hundreds (100s)": lambda x: f"{x / 1e2:.1f}H",
            "Thousands"      : lambda x: f"{x / 1e6:.1f}M" if abs(x / 1e3) >= 1000 else f"{x / 1e3:.1f}K",
            "Millions"       : lambda x: f"{x / 1e9:.1f}B" if abs(x / 1e6) >= 1000 else f"{x / 1e6:.1f}M",
            "Billions"       : lambda x: f"{x / 1e9:.1f}B"
        }

        selected_formatter = formatters.get(unit_str, lambda x: f"{x:g}")

        def formatter(x: Any, pos: Any) -> str:
            try:
                return selected_formatter(x)
            except (ValueError, TypeError):
                return f"{x:g}"

        return FuncFormatter(formatter)
