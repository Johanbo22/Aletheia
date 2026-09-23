import hashlib
import traceback
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

import pandas as pd
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from src.core.global_signals import LogLevel, ToastLevel, global_signals
from src.ui.dialogs import ProgressDialog
from src.ui.workers import PlotDataPrepWorker

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

class PlotGenerationManager:
    """
    Manager responsible for handling the plot generation lifecycle
    including data validation, background processing and strategy execution
    """

    PLOTS_NO_X: frozenset[str] = frozenset(
        ["Box", "Histogram", "KDE", "Heatmap", "Pie", "ECDF", "Eventplot", "GeoSpatial"])
    PLOTS_NO_Y: frozenset[str] = frozenset(["Count Plot", "Heatmap", "GeoSpatial"])
    PLOTS_GRIDDED: frozenset[str] = frozenset(["Image Show (imshow)", "pcolormesh", "Contour", "Contourf"])
    PLOTS_VECTOR: frozenset[str] = frozenset(["Barbs", "Quiver", "Streamplot"])
    PLOTS_3D: frozenset[str] = frozenset(["3D Line", "3D Scatter", "3D Surface"])
    PLOTS_STRICT_NUMERIC_2D: frozenset[str] = frozenset([
        "Scatter", "Hexbin", "2D Density", "2D Histogram", "Stem", "Stairs", "Triplot"
    ])
    PLOTS_NUMERIC_Y: frozenset[str] = frozenset([
        "Line", "Bar", "Area", "Box", "Violin", "Pie", "Stackplot",
        "Image Show (imshow)", "pcolormesh", "PColormesh", "Contour", "Contourf",
        "Barbs", "Quiver", "Streamplot", "Tricontour", "Tricontourf", "Tripcolor"
    ])
    PLOTS_DISTRIBUTION: frozenset[str] = frozenset(["Histogram", "KDE", "ECDF"])

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.thread_pool = plot_tab.thread_pool

    def generate_plot(self, animate: bool = True) -> None:
        """Trigger the plot execution based on current settings"""
        if getattr(self, "_is_generating", False):
            self.plot_tab.status_bar.log(f"Plot generation already in progress. Please wait", LogLevel.WARNING)
            return

        if self.plot_tab._is_clearing:
            return
        if not self.plot_tab.isVisible():
            self.plot_tab._is_data_dirty = True
            return
        if not self._validate_data_loaded():
            return

        self._is_generating = True

        try:
            subplot_index, frozen_config = self._get_subplot_config()
            active_df, config = self._resolve_data_config(subplot_index, frozen_config)

            if not self._validate_active_dataframe(active_df):
                self._is_generating = False
                return

            config["plot_type"] = self.plot_tab.current_plot_type_name
            z_col = self.view.z_column.currentText()
            is_valid, validation_msg = self._validate_plot_requirements(
                config["plot_type"], active_df, config["x_col"], config["y_cols"], z_col
            )
            if not is_valid:
                self._is_generating = False
                if validation_msg:
                    self.plot_tab.status_bar.log(validation_msg, LogLevel.WARNING)
                return

            self._execute_or_cache_plot(active_df, subplot_index, config, animate)
        except Exception:
            self._is_generating = False
            raise

    def _execute_or_cache_plot(
            self, active_df: pd.DataFrame, subplot_index: int, config: Dict[str, Any], animate: bool = True
    ) -> None:
        """Checks cache before initiating the background thread"""
        data_sig = self._build_data_signature(active_df, config)

        has_cached_df = getattr(self.plot_tab, "_cached_active_df", None) is not None
        has_last_sig = getattr(self.plot_tab, "_last_data_signature", None) == data_sig

        if has_last_sig and has_cached_df:
            self.plot_tab.status_bar.log("Using cached data for plotting", LogLevel.INFO)
            self.generate_main_plot(
                self.plot_tab._cached_active_df, subplot_index, config, keep_data=True, animate=animate
            )
            return

        self.plot_tab._last_data_signature = data_sig
        self._start_prep_worker(active_df, subplot_index, config, animate)

    def _start_prep_worker(
            self, active_df: pd.DataFrame, subplot_index: int, config: Dict[str, Any], animate: bool = True) -> None:
        """Starts the background thread for data preparation"""
        self.plot_tab.status_bar.log("Preparing data in background...", LogLevel.INFO)
        self.plot_tab._prep_progress_dialog = ProgressDialog(
            title="Preparing Data",
            message="Initializing background task...",
            parent=self.plot_tab
        )
        self.plot_tab._prep_progress_dialog.show()

        worker = PlotDataPrepWorker(
            active_df.copy(), config["plot_type"], config["x_col"],
            config["y_cols"], config["quick_filter"]
        )
        worker.signals.progress.connect(self.plot_tab._prep_progress_dialog.update_progress)
        worker.signals.log.connect(lambda msg: self.plot_tab.status_bar.log(msg, LogLevel.INFO))
        worker.signals.error.connect(self._on_prep_error)
        worker.signals.finished.connect(
            lambda procesed_df: self._on_prep_finished(procesed_df, subplot_index, config, animate)
        )
        self.thread_pool.start(worker)

    def _build_data_signature(self, active_df: pd.DataFrame, config: Dict[str, Any]) -> str:
        """Constructs a signature tuple to identify unchanged data states"""
        view = self.view
        axes_flipped = view.flip_axes_check.isChecked()
        x_scale = view.x_scale_combo.currentText()
        y_scale = view.y_scale_combo.currentText()

        x_dt_fmt = view.x_datetime_format_combo.currentText() if view.custom_datetime_check.isChecked() else None
        y_dt_fmt = view.y_datetime_format_combo.currentText() if view.custom_datetime_check.isChecked() else None
        x_dt_custom = view.x_custom_datetime_input.text() if x_dt_fmt == "Custom" else None
        y_dt_custom = view.y_custom_datetime_format_input.text() if y_dt_fmt == "Custom" else None

        signature_components = (
            id(self.plot_tab.data_handler.df),
            active_df.shape,
            config.get("plot_type"),
            config.get("x_col"),
            tuple(config.get("y_cols", [])) if config.get("y_cols") else None,
            config.get("subset_name"),
            config.get("quick_filter"),
            view.flip_axes_check.isChecked(),
            view.x_scale_combo.currentText(),
            view.y_scale_combo.currentText(),
            x_dt_fmt,
            y_dt_fmt,
            x_dt_custom,
            y_dt_custom,
            view.secondary_y_check.isChecked(),
            view.secondary_y_column.currentText(),
            view.secondary_plot_type_combo.currentText(),
            view.histogram_bins_spin.value(),
            view.histogram_show_normal_check.isChecked(),
            view.histogram_show_kde_check.isChecked(),
            view.bar_width_spin.value(),
            view.regression_line_check.isChecked(),
            view.regression_type_combo.currentText(),
            view.poly_degree_spin.value(),
            view.confidence_interval_check.isChecked(),
            view.show_r2_check.isChecked(),
            view.show_rmse_check.isChecked(),
            view.show_equation_check.isChecked(),
            view.confidence_level_spin.value(),
            view.pie_show_percentages_check.isChecked(),
            view.pie_start_angle_spin.value(),
            view.pie_explode_check.isChecked(),
            view.pie_explode_distance_spin.value(),
            view.pie_shadow_check.isChecked(),
            view.pie_donut_check.isChecked(),
            view.pie_donut_width_spin.value(),
            view.error_bars_combo.currentText(),
            view.error_bar_linewidth_spin.value(),
            view.error_bar_capsize_spin.value(),
            view.error_bar_alpha_slider.value(),
            view.error_bar_zorder_spin.value(),
        )

        signature_string = f"{signature_components}".encode('utf-8')
        return hashlib.sha256(signature_string).hexdigest()

    def _on_prep_error(self, error: Exception) -> None:
        """Handles errors from the background data preparation thread"""
        self._is_generating = False
        dialog = getattr(self.plot_tab, "_prep_progress_dialog", None)
        if dialog:
            dialog.accept()
        self.plot_tab.status_bar.log(f"Data preparation failed: {str(error)}", LogLevel.ERROR)
        global_signals.request_toast(
            "Data Preparation Error", "An error occurred during data processing", ToastLevel.ERROR
        )

    def _on_prep_finished(self, processed_df: pd.DataFrame, subplot_index: int, config: Dict[str, Any],
                          animate: bool = True) -> None:
        """Called when the background data preparation completes successfully"""
        dialog = getattr(self.plot_tab, "_prep_progress_dialog", None)
        if dialog:
            dialog.accept()

        self.plot_tab._cached_active_df = processed_df
        self.generate_main_plot(processed_df, subplot_index, config, keep_data=False, animate=animate)

    def _validate_data_loaded(self) -> bool:
        """Validates if data is present in DataHandler instance"""
        if self.plot_tab.data_handler.df is None:
            self.plot_tab.status_bar.log("No Data Loaded", LogLevel.WARNING)
            global_signals.request_toast("No Data Loaded", "Please load data first", ToastLevel.WARNING)
            return False
        return True

    def _get_subplot_config(self) -> Tuple[int, Optional[dict]]:
        """Retrieves the subplot indices and frozen configurations if active"""
        index = self.view.active_subplot_combo.currentIndex()
        if index < 0:
            index = 0

        frozen_cfg = None
        if self.view.freeze_data_check.isChecked() and self.view.add_subplots_check.isChecked():
            frozen_cfg = self.plot_tab.subplot_manager.get_config(index)

        return index, frozen_cfg

    def _resolve_data_config(self, subplot_index: int, frozen_cfg: Optional[dict]) -> Tuple[
        pd.DataFrame, Dict[str, Any]]:
        """Resolves config fields from UI"""
        if frozen_cfg:
            config = {
                "x_col"       : frozen_cfg.get("x_col"),
                "y_cols"      : frozen_cfg.get("y_cols"),
                "hue"         : frozen_cfg.get("hue"),
                "subset_name" : frozen_cfg.get("subset_name"),
                "quick_filter": frozen_cfg.get("quick_filter", "")
            }
            active_df = self._restore_frozen_data(config["subset_name"])
            self.plot_tab.status_bar.log(f"Using data config for plot {subplot_index + 1}", LogLevel.INFO)
        else:
            view = self.plot_tab.view
            config = {
                "x_col"       : view.x_column.currentText(),
                "y_cols"      : self.plot_tab.get_selected_y_columns(),
                "hue"         : view.hue_column.currentText() if view.hue_column.currentText() != "None" else None,
                "subset_name" : view.subset_combo.currentData() if view.use_subset_check.isChecked() else None,
                "quick_filter": view.quick_filter_input.text().strip()
            }
            active_df = self.plot_tab.get_active_dataframe()

        return active_df, config

    def _restore_frozen_data(self, subset_name: str) -> pd.DataFrame:
        """Retrieves stored data subsets for frozen configs"""
        if not subset_name:
            return self.plot_tab.data_handler.df

        try:
            if self.plot_tab.subset_manager:
                return self.plot_tab.subset_manager.apply_subset(
                    self.plot_tab.data_handler.df, subset_name
                )
            self.plot_tab.status_bar.log("Subset Manager not loaded", LogLevel.WARNING)
            return self.plot_tab.data_handler.df
        except Exception as e:
            self.plot_tab.status_bar.log(f"Restore Error: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Configuration Error", "Failed to retrieve data subsets", ToastLevel.ERROR)
            return self.plot_tab.data_handler.df

    def _validate_active_dataframe(self, active_df: pd.DataFrame) -> bool:
        if active_df is None or len(active_df) == 0:
            global_signals.request_toast("Data Is Empty", "Selected data is empty", ToastLevel.WARNING)
            return False
        return True

    def generate_main_plot(
            self, active_df: pd.DataFrame, subplot_index: int,
            config: Dict[str, Any], keep_data: bool = False, animate: bool = True
    ) -> None:
        """Orchestrates the synchronous Matplotlib rendering generation cycle."""
        dialog = None
        try:
            data_size = len(self.plot_tab.data_handler.df)
            show_prog = (data_size > 1000 and not keep_data)
            dialog = self._init_progress_dialog(show_prog, data_size)

            z_col = config.get("z_column")
            is_valid, validation_msg = self._validate_plot_requirements(
                config["plot_type"], active_df, config["x_col"], config["y_cols"], z_col
            )

            if not keep_data and not is_valid:
                if dialog:
                    dialog.accept()
                if validation_msg:
                    self.plot_tab.status_bar.log(validation_msg, LogLevel.WARNING)
                return

            self._update_progress(dialog, 20, "Building Plot Configuration")
            gen_kwargs, plot_kwargs = self._prepare_kwargs(config)

            self._apply_style_setup(keep_data, dialog)

            if not keep_data:
                self._update_progress(dialog, 40, f"Creating {config['plot_type']} plot")
                if not self._execute_strategy(active_df, config, plot_kwargs, gen_kwargs):
                    if dialog:
                        dialog.accept()
                    return

            self.plot_tab.formatting_manager.apply_plot_formatting(
                dialog, config["x_col"], config["y_cols"], gen_kwargs, active_df
            )

            self._update_progress(dialog, 98, "Finishing up")
            self._finalize_plot(subplot_index, config, is_fast_render=keep_data)

            if not keep_data:
                self._log_plot_message(active_df, config)
            self._update_progress(dialog, 100, "Complete")

            if dialog:
                QTimer.singleShot(300, dialog.accept)
            self.plot_tab._is_data_dirty = False
            if hasattr(self.plot_tab, "selection_overlay"):
                self.plot_tab.selection_overlay.show_update_required(False)

            if animate:
                global_signals.toast_requested.emit(
                    "Plot Generated", f"A {config['plot_type']} plot has been generated",
                    ToastLevel.SUCCESS, 4000
                )
        except InterruptedError:
            self.plot_tab.status_bar.log("Plot generation cancelled", LogLevel.INFO)
            if dialog:
                dialog.accept()
        except Exception as e:
            if dialog:
                dialog.accept()
            self._handle_generation_error(e)
        finally:
            self._is_generating = False

    def _prepare_kwargs(self, config: Dict[str, Any]) -> Tuple[dict, dict]:
        fmt_mgr = self.plot_tab.formatting_manager
        gen_kw = fmt_mgr.build_general_kwargs(config["plot_type"], config["x_col"], config["y_cols"], config["hue"])
        plt_kw = fmt_mgr.build_plot_specific_kwargs(config["plot_type"])
        return gen_kw, plt_kw

    def _apply_style_setup(self, keep_data: bool, dialog: Optional[ProgressDialog]) -> None:
        if not keep_data:
            self._update_progress(dialog, 30, "Clearing Previous plot")
            self.plot_tab.formatting_manager.setup_plot_figure(clear=True)
        else:
            self.plot_tab.formatting_manager.setup_plot_figure(clear=False)

        self._update_progress(dialog, 35, "Setting plot style")
        self.plot_tab.formatting_manager.apply_plot_style()
        self.plot_tab.formatting_manager.set_axis_limit_and_scales()

    def _execute_strategy(
            self, active_df: pd.DataFrame, config: Dict[str, Any], plt_kw: dict, gen_kw: dict
    ) -> bool:
        original_df = self.plot_tab.data_handler.df
        self.plot_tab.data_handler.df = active_df
        axes_flipped = self.plot_tab.view.flip_axes_check.isChecked()
        font_family = self.plot_tab.view.font_family_combo.currentText()

        try:
            error_msg = self.plot_tab.plot_engine.execute_strategy(
                plot_type=config["plot_type"],
                plot_tab=self.plot_tab,
                x_col=config["x_col"],
                y_cols=config["y_cols"],
                axes_flipped=axes_flipped,
                font_family=font_family,
                plot_kwargs=plt_kw,
                general_kwargs=gen_kw
            )

            if error_msg:
                global_signals.request_toast("Error", error_msg, ToastLevel.ERROR)
                self.plot_tab.status_bar.log(f"Plot execution error: {error_msg}", LogLevel.ERROR)
                return False
            return True
        finally:
            self.plot_tab.data_handler.df = original_df

    def _finalize_plot(self, subplot_index: int, config: Dict[str, Any], is_fast_render: bool = False) -> None:
        try:
            if self.plot_tab.view.tight_layout_check.isChecked():
                self.plot_tab.plot_engine.finalize_layout()
        except Exception as e:
            msg = str(e)
            if "ParseSyntaxException" not in msg and "math text" not in msg.lower():
                self.plot_tab.status_bar.log(f"Tight layout error: {msg}", LogLevel.ERROR)

        self.plot_tab.canvas.draw()
        if hasattr(self.plot_tab, "canvas_stack"):
            self.plot_tab.canvas_stack.setCurrentWidget(self.plot_tab.canvas)

        if not is_fast_render:
            self.plot_tab.subplot_manager.update_overlay()

        if self.plot_tab.view.add_subplots_check.isChecked():
            self.plot_tab.subplot_manager.save_config(subplot_index, config)

        if self.plot_tab.view.multiline_custom_check.isChecked():
            self.plot_tab.series_customization_manager.update_line_selector(preserve_selection=True)
        if self.plot_tab.view.multibar_custom_check.isChecked():
            self.plot_tab.series_customization_manager.update_bar_selector(preserve_selection=True)

        self.plot_tab.script_manager.sync_script_if_open()

    def _handle_generation_error(self, e: Exception) -> None:
        error_msg = str(e)
        if "ParseSyntaxException" in error_msg or "math text" in error_msg.lower():
            self.plot_tab.status_bar.log("Incomplete LaTeX math expression detected.", LogLevel.WARNING)
        else:
            global_signals.request_toast("Error", "Failed to generate plot", ToastLevel.ERROR)
            self.plot_tab.status_bar.log(f"Plot generation failed: {error_msg}", LogLevel.ERROR)
            traceback.print_exc()

    def _init_progress_dialog(self, show_progress: bool, data_size: int) -> Optional[ProgressDialog]:
        if not show_progress:
            return None
        dialog = ProgressDialog("Generating plot", f"Processing {data_size:,} data points", parent=self.plot_tab)
        dialog.show()
        dialog.update_progress(5, "Initializing plotting engine")
        QApplication.processEvents()
        return dialog

    def _update_progress(self, dialog: Optional[ProgressDialog], value: int, message: str) -> None:
        if dialog:
            dialog.update_progress(value, message)
            if dialog.is_cancelled():
                self.plot_tab.status_bar.log("Plot generation cancelled", LogLevel.WARNING)
                raise InterruptedError("User cancelled")

    def _validate_plot_requirements(self, plot_type: str, df: Optional[pd.DataFrame] = None,
                                    x_col: Optional[str] = None, y_cols: Optional[List[str]] = None,
                                    z_col: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validates the prescence, dimension counts and data type suitablity for the selected axes

        :param plot_type: Target plot type
        :param df: Active daataframe instance under evaluation
        :param x_col: Name of selected x axis column
        :param y_cols: Name of selected y axis columns
        :param z_col: Name of selected z axis column for 3D / gridded plots
        :return: Tuple of validity and optional error message
        """
        target_df = df if df is not None else self.plot_tab.data_handler.df
        if target_df is None or target_df.empty:
            return False, "No active dataset loaded for plotting"

        target_x = x_col if x_col is not None else self.view.x_column.currentText()
        target_y = y_cols if y_cols is not None else self.plot_tab.get_selected_y_columns()
        target_z = z_col if z_col is not None else (
            self.view.z_column.currentText() if hasattr(self.view, "z_column") else None
        )

        is_present, presence_err = self._validate_column_presence(
            plot_type, target_df, target_x, target_y, target_z
        )
        if not is_present:
            return False, presence_err

        return self._validate_column_types(
            plot_type, target_df, target_x, target_y, target_z
        )

    def _validate_column_presence(
            self,
            plot_type: str,
            df: pd.DataFrame,
            x_col: str,
            y_cols: List[str],
            z_col: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Verify required columns are selected and exists"""
        if plot_type == "GeoSpatial":
            if "geometry" not in df.columns:
                return False, "GeoSpatial plot requires a dataset with a 'geometry' column."
            return True, None

        if plot_type not in self.PLOTS_NO_X:
            if not x_col or x_col not in df.columns:
                return False, f"Please select a valid X column for {plot_type}."

        if plot_type not in self.PLOTS_NO_Y:
            if not y_cols or not any(col in df.columns for col in y_cols):
                return False, f"Please select at least one valid Y column for {plot_type}."

        if plot_type in self.PLOTS_GRIDDED and len(y_cols) < 2:
            return False, f"{plot_type} requires 2 Y columns (Y-axis and Z-value)."

        if plot_type in self.PLOTS_VECTOR and len(y_cols) < 3:
            return False, f"{plot_type} requires 3 Y columns (Y, U, V)."

        if plot_type == "Stackplot" and len(y_cols) < 2:
            return False, "Stackplot requires at least two Y columns."

        if plot_type in self.PLOTS_3D:
            if not z_col or z_col == "None" or z_col not in df.columns:
                return False, f"{plot_type} requires a valid Z Column mapped in General Settings."

        return True, None

    def _validate_column_types(
            self,
            plot_type: str,
            df: pd.DataFrame,
            x_col: str,
            y_cols: List[str],
            z_col: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Verify selected column data types match plot type constraints."""
        if plot_type in self.PLOTS_3D:
            if not pd.api.types.is_numeric_dtype(df[x_col]):
                return False, f"{plot_type} requires numeric X column. '{x_col}' is not numeric."
            if not pd.api.types.is_numeric_dtype(df[y_cols[0]]):
                return False, f"{plot_type} requires numeric Y column. '{y_cols[0]}' is not numeric."
            if z_col and not pd.api.types.is_numeric_dtype(df[z_col]):
                return False, f"{plot_type} requires numeric Z column. '{z_col}' is not numeric."
            return True, None

        if plot_type in self.PLOTS_STRICT_NUMERIC_2D:
            if not (pd.api.types.is_numeric_dtype(df[x_col]) or pd.api.types.is_datetime64_any_dtype(df[x_col])):
                return False, f"{plot_type} requires a numeric or datetime X column. '{x_col}' is not suitable."
            if not pd.api.types.is_numeric_dtype(df[y_cols[0]]):
                return False, f"{plot_type} requires a numeric Y column. '{y_cols[0]}' is not suitable."
            return True, None

        if plot_type in self.PLOTS_NUMERIC_Y:
            for y_col in y_cols:
                if y_col in df.columns and not pd.api.types.is_numeric_dtype(df[y_col]):
                    return False, f"{plot_type} requires a numeric Y column. '{y_col}' is not numeric."
            return True, None

        if plot_type in self.PLOTS_DISTRIBUTION:
            target_col = y_cols[0] if (y_cols and y_cols[0] in df.columns) else x_col
            if target_col in df.columns and not pd.api.types.is_numeric_dtype(df[target_col]):
                return False, f"{plot_type} requires a numeric data column. '{target_col}' is not numeric."
            return True, None

        return True, None

    def _log_plot_message(self, active_df: pd.DataFrame, config: Dict[str, Any]) -> None:
        plot_details = {
            "plot_type"  : config["plot_type"],
            "x_column"   : config["x_col"],
            "y_column"   : str(config["y_cols"]),
            "data_points": len(self.plot_tab.data_handler.df),
            "annotations": len(self.plot_tab.annotation_manager.annotations)
        }
        if config["hue"]:
            plot_details["hue"] = config["hue"]
        if config["quick_filter"]:
            plot_details["filter"] = config["quick_filter"]

        status_msg = f"{config['plot_type']} plot created"
        if self.plot_tab.view.use_subset_check.isChecked() and config["subset_name"]:
            plot_details.update({"subset": config["subset_name"], "subset_rows": len(active_df)})
            status_msg += f" (Subset: {config['subset_name']})"

        if self.plot_tab.annotation_manager.annotations:
            status_msg += f" with {len(self.plot_tab.annotation_manager.annotations)} annotations"

        self.plot_tab.status_bar.log_action(status_msg, details=plot_details, level="SUCCESS")
