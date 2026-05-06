import traceback
from typing import TYPE_CHECKING

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
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
                    "pandas", "numpy", "matplotlib", "seaborn", "scipy", "math", "datetime", "random", "re", "io", "typing", "collections", "itertools", "functools"
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

    def _sync_gui_from_ax(self, ax) -> None:
        """Attempts to update the GUI fields from the resulting plot"""
        try:
            title = ax.get_title()
            if title:
                self.plot_tab.view.title_input.setText(title)
                self.plot_tab.view.title_check.setChecked(True)

            xlabel = ax.get_xlabel()
            if xlabel:
                self.plot_tab.view.xlabel_input.setText(xlabel)
                self.plot_tab.view.xlabel_check.setChecked(True)

            ylabel = ax.get_ylabel()
            if ylabel:
                self.plot_tab.view.ylabel_input.setText(ylabel)
                self.plot_tab.view.ylabel_check.setChecked(True)

        except Exception as GUISyncError:
            print(f"Warning could not sync GUI from plot: {GUISyncError}")
