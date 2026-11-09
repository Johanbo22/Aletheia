from typing import Optional, Sequence, TYPE_CHECKING, TypedDict

from PyQt6.QtWidgets import QMessageBox

from src.ui.status_bar import LogLevel

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

GridSpanTuple = tuple[int, int, int, int]
DEFAULT_GRID_SIZE: int = 2
SINGLE_PLOT_SIZE: int = 1

class SubplotDataConfig(TypedDict, total=False):
    """Represents the data configuration of a single subplot"""
    plot_type: str
    x_col: Optional[str]
    y_cols: list[str]
    hue: Optional[str]
    subset_name: Optional[str]
    quick_filter: str

class SubplotsStateDict(TypedDict, total=False):
    """Represents the serialized subplot layout state"""
    enabled: bool
    rows: int
    cols: int
    custom_grid: Sequence[Sequence[int]]
    active_subplot: int
    sharex: bool
    sharey: bool
    freeze_data: bool
    subplot_configs: dict[str, SubplotDataConfig]

class SubplotManager:
    """
    Manages subplot layouts, active subplot selections
    and individual subplot data configs
    """

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.plot_engine = plot_tab.plot_engine
        self.selection_overlay = plot_tab.selection_overlay

        # State tracking for frozen data for subplots
        self.subplot_data_configs: dict[int, SubplotDataConfig] = {}

    def connect_signals(self) -> None:
        self.view.grid_designer.layout_applied.connect(self.apply_custom_grid_layout)
        self.view.active_subplot_combo.currentIndexChanged.connect(self.on_active_subplot_changed)
        self.view.add_subplots_check.stateChanged.connect(self.on_subplot_active)

    def on_subplot_active(self) -> None:
        """Toggle the subplot configuration panel and synchronize the canvas"""
        subplots_enabled: bool = self.view.add_subplots_check.isChecked()
        self.view.subplot_group.setVisible(subplots_enabled)

        if not subplots_enabled:
            self._populate_subplot_combo(plot_count=SINGLE_PLOT_SIZE, active_index=0)
            self.plot_tab.clear_plot()
            self.selection_overlay.hide()
            self.clear_configs()
            return

        rows: int = self.view.grid_designer.rows_spin.value()
        cols: int = self.view.grid_designer.cols_spin.value()
        custom_grid: list[GridSpanTuple] = self.view.grid_designer.get_custom_grid()
        self.sync_layout(rows=rows, cols=cols, custom_grid=custom_grid, active_index=0)

    def _populate_subplot_combo(self, plot_count: int, active_index: int = 0) -> int:
        """
        Construct the subplot combo and select the target index
        :param plot_count: Total number of subplots i the active layout
        :param active_index: Index of subplot to select
        :return: The active subplot index
        """
        safe_count: int = max(SINGLE_PLOT_SIZE, plot_count)
        clamped_index: int = max(0, min(active_index, safe_count - 1))

        self.view.active_subplot_combo.blockSignals(True)
        self.view.active_subplot_combo.clear()
        for idx in range(safe_count):
            self.view.active_subplot_combo.addItem(f"Plot {idx + 1}")
        self.view.active_subplot_combo.setCurrentIndex(clamped_index)
        self.view.active_subplot_combo.blockSignals(False)

        return clamped_index

    def sync_layout(
            self,
            rows: int,
            cols: int,
            custom_grid: list[GridSpanTuple],
            active_index: int = 0
    ) -> None:
        """
        Synchronize the figure layout and active subplot selections
        :param rows: Number of grid rows
        :param cols: Number of grid columns
        :param custom_grid: List of row_start, row_end, col_start, col_end grid positions
        :param active_index: Subplot index to activate after layout creation
        """
        sharex: bool = self.view.subplot_sharex_check.isChecked()
        sharey: bool = self.view.subplot_sharey_check.isChecked()

        try:
            self.plot_engine.setup_layout(
                rows=rows,
                cols=cols,
                sharex=sharex,
                sharey=sharey,
                custom_grid=custom_grid
            )
            clamped_index: int = self._populate_subplot_combo(
                plot_count=len(custom_grid),
                active_index=active_index
            )
            self.plot_tab.canvas.draw()
            self.on_active_subplot_changed(clamped_index)
            self.status_bar.log(
                f"Subplot layout updated {rows}x{cols} with ({len(custom_grid)}) plots",
                LogLevel.INFO
            )
        except (ValueError, TypeError, RuntimeError) as layout_err:
            self.status_bar.log(
                f"Failed to apply custom grid layout: {str(layout_err)}",
                LogLevel.ERROR
            )

    def apply_custom_grid_layout(self, rows: int, cols: int, custom_grid: list[GridSpanTuple]) -> None:
        """Prompt user for confirmation and apply the custom GridSpec layout to the canvas"""
        confirmation = QMessageBox.question(
            self.plot_tab,
            "Update Layout",
            "Updating subplot layout will clear all existing plots on the canvas.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        self.clear_configs()
        self.sync_layout(rows=rows, cols=cols, custom_grid=custom_grid, active_index=0)

    def on_active_subplot_changed(self, index: int) -> None:
        """Changes the index of the active subplot"""
        if index >= 0:
            self.plot_engine.set_active_subplot(index)
            self.update_overlay()
            self.status_bar.log(f"Active subplot set to: {index + 1}", LogLevel.INFO)
        else:
            self.selection_overlay.hide()

    def update_overlay(self, is_resize: bool = False) -> None:
        """Recalculates the geometry and overlay widgets"""
        geometry = self.plot_engine.get_active_axis_geometry()

        if geometry:
            x, y, w, h = geometry
            current_text = self.view.active_subplot_combo.currentText()
            self.selection_overlay.update_info(current_text, (x, y, w, h), is_resize=is_resize)
        else:
            self.selection_overlay.hide()

    def save_config(self, index: int, config: SubplotDataConfig) -> None:
        """
        Save the data selection state for a specific subplot index

        :param index: Subplot index
        :param config: Data configuration dict for the subplot
        """
        self.subplot_data_configs[index] = config

    def get_config(self, index: int) -> Optional[SubplotDataConfig]:
        """
        Retrieve the stored dat configuration for a subplot index
        :param index: Subplot index
        :return: The stored SubplotDataConfig, if it exists else None
        """
        return self.subplot_data_configs.get(index)

    def clear_configs(self) -> None:
        """Clear all stored subplot data configs"""
        self.subplot_data_configs.clear()

    def export_configs(self) -> dict[str, SubplotDataConfig]:
        """
        Serialize subplot data configs into a JSON structure
        :return: Dictionary of subplot indicies and their data configs
        """
        return {str(index): cfg for index, cfg in self.subplot_data_configs.items()}

    @staticmethod
    def _normalize_custom_grid(
            raw_grid: Optional[Sequence[Sequence[int]]]
    ) -> Optional[list[GridSpanTuple]]:
        """Convert the JSON span lists into 4-ints tuples"""
        if not raw_grid:
            return None

        normalized: list[GridSpanTuple] = []
        for span in raw_grid:
            if len(span) == 4:
                normalized.append((int(span[0]), int(span[1]), int(span[2]), int(span[3])))
        return normalized or None

    def restore_from_config(self, subplots_config: SubplotsStateDict) -> None:
        """Restore the subplot UI controls, GridSpec designer widget and canvas layout from the saved configuration"""
        enabled: bool = bool(subplots_config.get("enabled", False))
        rows: int = int(subplots_config.get("rows", DEFAULT_GRID_SIZE))
        cols: int = int(subplots_config.get("cols", DEFAULT_GRID_SIZE))
        sharex: bool = bool(subplots_config.get("sharex", False))
        sharey: bool = bool(subplots_config.get("sharey", False))
        freeze_data: bool = bool(subplots_config.get("freeze_data", False))
        active_index: int = int(subplots_config.get("active_subplot", 0))
        normalized_grid = self._normalize_custom_grid(subplots_config.get("custom_grid"))

        self.view.subplot_sharex_check.blockSignals(True)
        self.view.subplot_sharey_check.blockSignals(True)
        self.view.subplot_sharex_check.setChecked(sharex)
        self.view.subplot_sharey_check.setChecked(sharey)
        self.view.subplot_sharex_check.blockSignals(False)
        self.view.subplot_sharey_check.blockSignals(False)

        self.view.freeze_data_check.setChecked(freeze_data)
        self.view.grid_designer.set_shared_axes(sharex, sharey)
        self.view.grid_designer.set_custom_grid(
            rows=rows,
            cols=cols,
            custom_grid=normalized_grid,
        )

        self.view.add_subplots_check.blockSignals(True)
        self.view.add_subplots_check.setChecked(enabled)
        self.view.add_subplots_check.blockSignals(False)
        self.view.subplot_group.setVisible(enabled)

        self.clear_configs()
        raw_configs = subplots_config.get("subplot_configs", {})
        if isinstance(raw_configs, dict):
            for key, cfg in raw_configs.items():
                try:
                    self.subplot_data_configs[int(key)] = cfg
                except (ValueError, TypeError):
                    continue

        if not enabled:
            self._populate_subplot_combo(plot_count=SINGLE_PLOT_SIZE, active_index=0)
            self.plot_engine.setup_layout(SINGLE_PLOT_SIZE, SINGLE_PLOT_SIZE)
            self.selection_overlay.hide()
            return

        active_spans: list[GridSpanTuple] = self.view.grid_designer.get_custom_grid()
        self.sync_layout(
            rows=self.view.grid_designer.rows_spin.value(),
            cols=self.view.grid_designer.cols_spin.value(),
            custom_grid=active_spans,
            active_index=active_index,
        )
