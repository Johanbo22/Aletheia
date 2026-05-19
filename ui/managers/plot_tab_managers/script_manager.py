import traceback
import copy
from typing import TYPE_CHECKING

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
from matplotlib.colors import to_hex
from scipy.stats import t as t_dist
from matplotlib.ticker import MaxNLocator
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer

from ui.dialogs import ScriptEditorDialog

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class ScriptManager:
    """Manages the script editor dialog and code execution"""

    SCRIPT_SYNC_TIMER_MS: int = 500

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.script_editor = None
        self.script_sync_timer = QTimer()
        self.script_sync_timer.setSingleShot(True)
        self.script_sync_timer.setInterval(self.SCRIPT_SYNC_TIMER_MS)
        self.script_sync_timer.timeout.connect(self._perform_script_sync)

    def sync_script_if_open(self) -> None:
        """Regenerates the script and updates the editor if its is open and autosync is enabled"""
        if self.script_editor and self.script_editor.isVisible():
            self.script_sync_timer.start()
            self._perform_script_sync()

    def _perform_script_sync(self) -> None:
        config = self.plot_tab.get_config()
        df = self.plot_tab.get_active_dataframe()
        if df is not None:
            code = self.plot_tab.code_exporter.get_plot_script_only(df, config)
            self.script_editor.update_code(code)

    def open_script_editor(self) -> None:
        """Opens the Python script editor dialog"""
        if self.plot_tab.data_handler.df is None:
            QMessageBox.warning(self.plot_tab, "No Data", "Please load data first before opening the editor")
            return

        # Start by generating initial code
        config = self.plot_tab.get_config()
        df = self.plot_tab.get_active_dataframe()
        if df is None:
            return

        code = self.plot_tab.code_exporter.get_plot_script_only(df, config)

        # Open dialog
        if self.script_editor is None:
            self.script_editor = ScriptEditorDialog(code, df=df, parent=self.plot_tab)
            self.script_editor.run_script_signal.connect(self.run_custom_script)

        if not self.script_editor.isVisible():
            self.script_editor.update_code(code)
            self.script_editor.show()
        else:
            self.script_editor.raise_()
            self.script_editor.activateWindow()
            self.sync_script_if_open()

    def run_custom_script(self, script_content: str) -> None:
        """Executes the script from the editor. Overrides the standard plotting sequence"""
        self.plot_tab.status_bar.log("Running custom script...", "INFO")
        try:
            def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                allowed_modules = {
                    "pandas", "numpy", "matplotlib", "seaborn", "scipy", "math", "datetime", "random", "re", "io", "typing", "collections", "itertools", "functools", "sqlalchemy", "traceback", "requests"
                }
                base_name = name.split(".")[0]
                if base_name not in allowed_modules:
                    raise ImportError(f"Import of module: '{name}' is restricted in current namespace")
                return __import__(name, globals, locals, fromlist, level)

            safe_globals = {
                "__builtins__": {
                    "__import__": safe_import,
                    "print": print, "range": range, "len": len, "list": list, "dict": dict, "set": set, "str": str,
                    "int": int, "float": float, "bool": bool,
                    "zip": zip, "enumerate": enumerate, "min": min, "max": max, "sum": sum, "abs": abs, "sorted": sorted,
                    "tuple": tuple, "None": None,
                    "True": True, "False": False, "hasattr": hasattr, "getattr": getattr, "isinstance": isinstance
                },
                "pd": pd, "np": np, "plt": plt, "sns": sns, "mdates": mdates, "t_dist": t_dist,
                "MaxNLocator": MaxNLocator
            }

            df_active = self.plot_tab.get_active_dataframe().copy()
            local_vars = {"df": df_active}

            exec(script_content, safe_globals, local_vars)

            if "create_plot" not in local_vars:
                raise ValueError("Script must define the function name 'create_plot' that returns (fix, ax)")

            create_plot_func = local_vars["create_plot"]

            self.plot_tab.plot_engine.clear_plot()
            fig_result, ax_result = create_plot_func(df_active)

            old_fig = self.plot_tab.plot_engine.current_figure
            if old_fig is not None:
                plt.close(old_fig)

            self.plot_tab.plot_engine.current_figure = fig_result
            self.plot_tab.plot_engine.current_ax = ax_result

            self.plot_tab.canvas.figure = fig_result
            fig_result.set_canvas(self.plot_tab.canvas)
            self.plot_tab.canvas.draw()

            self._sync_gui_from_ax(ax_result)
            self.plot_tab.status_bar.log("Script Executed", "SUCCESS")
        except Exception as ExecuteScriptError:
            QMessageBox.critical(self.plot_tab, "Script Error", f"An error occurred while running the script:\n{str(ExecuteScriptError)}")
            self.plot_tab.status_bar.log(f"Script execution failed: {str(ExecuteScriptError)}", "ERROR")
            traceback.print_exc()

    def _sync_gui_from_ax(self, ax: plt.Axes) -> None:
        """
        Synchronizes the UI elements by extracting properties from the executed script.
        Overrides the current plot_config and reloads it back into the canvas.
        """
        config = copy.deepcopy(self.plot_tab.get_config())
        fig = ax.figure

        try:
            self._sync_label(config, "appearance", "title", ax.get_title())
            self._sync_label(config, "appearance", "xlabel", ax.get_xlabel())
            self._sync_label(config, "appearance", "ylabel", ax.get_ylabel())

            self._sync_axis_limits(config, "x_axis", ax.get_xlim())
            self._sync_axis_limits(config, "y_axis", ax.get_ylim())
            config["axes"]["x_axis"]["scale"] = ax.get_xscale()
            config["axes"]["y_axis"]["scale"] = ax.get_yscale()

            legend = ax.get_legend()
            config["legend"]["enabled"] = legend is not None
            if legend:
                title_obj = legend.get_title()
                if title_obj:
                    config["legend"]["title"] = title_obj.get_text()

            has_grid = bool(ax.xaxis.get_gridlines() or ax.yaxis.get_gridlines())
            config["grid"]["enabled"] = has_grid

            spines_cfg = config.get("appearance", {}).get("spines", {})
            for side, spine in ax.spines.items():
                if side in spines_cfg:
                    spines_cfg[side]["visible"] = spine.get_visible()
                    try:
                        color = spine.get_edgecolor()
                        if color and color != "none":
                            spines_cfg[side]["color"] = to_hex(color, keep_alpha=False)
                    except Exception:
                        pass
                    try:
                        spines_cfg[side]["width"] = spine.get_linewidth()
                    except Exception:
                        pass

            try:
                x_params = ax.xaxis.get_tick_params()
                x_axis_cfg = config["axes"]["x_axis"]
                x_axis_cfg["tick_label_size"] = x_params.get("labelsize", x_axis_cfg["tick_label_size"])
                if "labelrotation" in x_params:
                    x_axis_cfg["tick_rotation"] = x_params["labelrotation"]

                y_params = ax.yaxis.get_tick_params()
                y_axis_cfg = config["axes"]["y_axis"]
                y_axis_cfg["tick_label_size"] = y_params.get("labelsize", y_axis_cfg["tick_label_size"])
                if "labelrotation" in y_params:
                    y_axis_cfg["tick_rotation"] = y_params["labelrotation"]
            except Exception:
                pass

            if fig:
                w, h = fig.get_size_inches()
                fig_cfg = config["appearance"]["figure"]
                fig_cfg["width"] = float(w)
                fig_cfg["height"] = float(h)
                fig_cfg["dpi"] = int(fig.get_dpi())

            self.plot_tab.config_manager.load_config(config)
        except Exception as sync_error:
            self.plot_tab.status_bar.log(f"Failed to sync GUI from script: {str(sync_error)}", "WARNING")

    def _sync_label(self, config: dict, section: str, key: str, value: str) -> None:
        """Sync text labels and enabled them if populated"""
        if value and str(value).strip():
            config[section][key]["text"] = str(value)
            config[section][key]["enabled"] = True

    def _sync_axis_limits(self, config: dict, axis_key: str, limits: tuple) -> None:
        """Sync axis limits and disable auto-limits"""
        axis_cfg = config["axes"][axis_key]
        try:
            axis_cfg["min"] = float(limits[0])
            axis_cfg["max"] = float(limits[1])
            axis_cfg["auto_limits"] = False
        except Exception:
            pass