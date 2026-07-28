from typing import Any, TYPE_CHECKING

from core.global_signals import ToastLevel, global_signals
from ui.dialogs.PlotExportDialog import PlotExportDialog
from ui.status_bar import LogLevel

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class PlotExportManager:
    """
    Manages exporting and saving plots to disk
    """

    def __init__(self, plot_tab: 'PlotTab') -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.canvas = plot_tab.canvas
        self.plot_engine = plot_tab.plot_engine
        self.status_bar = plot_tab.status_bar

    def save_plot_image(self) -> None:
        """Invokes the PlotExportDialog to save the current plot figure to disk"""
        if self.plot_engine.current_figure is None:
            global_signals.request_toast(
                "No Plot", "No plot available to save", ToastLevel.WARNING
            )
            return

        try:
            config = self._get_export_configuration()
            if not config or not config.get("filepath"):
                return

            self._execute_export(config)
            self._handle_export_success(config["filepath"])

        except PermissionError:
            self._handle_permission_error()
        except Exception as e:
            self._handle_general_error(e)

    def _get_export_configuration(self) -> dict | None:
        """Handles the PlotExportDialog invoke to get the export configuration"""
        preview_pixmap = self._get_preview_pixmap()
        fig_width, fig_height = self.plot_engine.current_figure.get_size_inches()

        dialog = PlotExportDialog(
            current_dpi=300,
            preview_pixmap=preview_pixmap,
            fig_width=fig_width,
            fig_height=fig_height,
            parent=self.plot_tab
        )

        if dialog.exec():
            return dialog.get_config()

        return None

    def _get_preview_pixmap(self) -> Any:
        """Grabs the canvas preview while hiding the selection overlay widget"""
        hidden_overlays = self._hide_overlay_widgets()

        preview_pixmap = self.canvas.grab()

        self._restore_overlay_widgets(hidden_overlays)

        return preview_pixmap

    def _execute_export(self, config: dict) -> None:
        """Performs the actual file saving with the specified configuration."""
        filepath: str = config["filepath"]

        kwargs = {
            "dpi"        : config["dpi"],
            "bbox_inches": "tight" if config["tight_layout"] else None,
            "transparent": config["transparent"]
        }

        if not config["transparent"]:
            kwargs["facecolor"] = self.plot_tab.bg_color

        original_size = self.plot_engine.current_figure.get_size_inches()
        target_size = (config["width"], config["height"])

        hidden_overlays = self._hide_overlay_widgets()

        try:
            self.plot_engine.current_figure.set_size_inches(*target_size)
            self.plot_engine.current_figure.savefig(filepath, **kwargs)
        finally:
            self.plot_engine.current_figure.set_size_inches(*original_size)
            self.canvas.draw_idle()
            self._restore_overlay_widgets(hidden_overlays)

    def _hide_overlay_widgets(self) -> list[Any]:
        """
        Hides UI overlay widgets to prevent them from being rendered
        in the preview and in final export.
        :return: A list of widgets that were hidden so they can be restored later
        """
        hidden_widgets: list[Any] = []
        overlay_attributes: list[str] = ["selection_overlay", "view_cube", "view_cube_widget"]

        for parent in (self.plot_tab, self.canvas):
            for attribute in overlay_attributes:
                if hasattr(parent, attribute):
                    widget = getattr(parent, attribute)
                    if hasattr(widget, "isVisible") and widget.isVisible():
                        if widget not in hidden_widgets:
                            widget.hide()
                            hidden_widgets.append(widget)
        return hidden_widgets

    def _restore_overlay_widgets(self, widgets: list[Any]) -> None:
        """Restores the visibility of previously hidden overlay widgets"""
        for widget in widgets:
            if hasattr(widget, "show"):
                widget.show()

    def _handle_export_success(self, filepath: str) -> None:
        """Handles UI updates on successful export."""
        self.status_bar.log_action(f"Plot saved to {filepath}", level=LogLevel.SUCCESS)
        global_signals.request_toast(
            "Plot Saved", f"Plot saved to:\n{filepath}", ToastLevel.SUCCESS
        )

    def _handle_permission_error(self) -> None:
        """Displays error when the file is locked by the OS."""
        self.status_bar.log("Permission denied: Target file might be open in another program.", LogLevel.ERROR)
        global_signals.request_toast(
            "Save Error", "Cannot save the file due to permissions", ToastLevel.ERROR
        )

    def _handle_general_error(self, e: Exception) -> None:
        """Displays generic export errors."""
        self.status_bar.log(f"Failed to save plot: {str(e)}", LogLevel.ERROR)
        global_signals.request_toast(
            "Save Error", f"Could not save plot", ToastLevel.ERROR
        )
