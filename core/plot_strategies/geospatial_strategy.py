from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple
import pandas as pd
from core.plot_strategies.base_strategy import BasePlotStrategy

try:
    import geopandas as gpd
    from mpl_toolkits.axes_grid1 import make_axes_locatable
except ImportError:
    gpd = None

try:
    import contextily as ctx
except ImportError:
    ctx = None

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab


class GeoSpatialPlotStrategy(BasePlotStrategy):
    """Strategy for generating GeoSpatial plots."""

    def _handle_geospatial_crs(self, gdf: Any, target_crs: Optional[str], add_basemap: bool) -> Any:
        if gdf.crs is None:
            print("Warning. Data has no CRS defined")
            try:
                gdf.set_crs("EPSG:4326", allow_override=True)
            except Exception as SetCRSError:
                print(f"Failed to set default CRS: {SetCRSError}")

        if target_crs and target_crs.lower() != "none" and target_crs.strip():
            try:
                gdf = gdf.to_crs(target_crs)
            except Exception as CRSInfo:
                print(f"Warning: Coordinate Reference System Transformation failed: {str(CRSInfo)}")

        if add_basemap and ctx:
            if not target_crs:
                try:
                    if gdf.crs and gdf.crs.to_string() != "EPSG:3857":
                        gdf = gdf.to_crs("EPSG:3857")
                except Exception as ReprojectionError:
                    print(f"Warning: Auto-projection for basemap failed: {str(ReprojectionError)}")

        return gdf

    def _configure_geospatial_legend(self, gdf: Any, column: Optional[str], legend: bool, orientation: Optional[str],
                                     legend_kwds: Dict[str, Any], use_divider: bool, kwargs: Dict[str, Any]) -> Tuple[
        bool, bool, Dict[str, Any]]:
        if legend_kwds is None:
            legend_kwds = {}
        if use_divider and column:
            legend = True

        is_categorical = False
        if column and column in gdf:
            col_dtype = gdf[column].dtype
            if pd.api.types.is_categorical_dtype(col_dtype) or pd.api.types.is_object_dtype(col_dtype):
                is_categorical = True
            if kwargs.get("categorical", False):
                is_categorical = True
            if kwargs.get("scheme", "None") != "None":
                is_categorical = False

        if not is_categorical:
            legend_kwds.pop("loc", None)
            kwargs.pop("loc", None)

            if isinstance(orientation, str):
                orientation = orientation.lower()
                legend_kwds["orientation"] = orientation

        if legend and orientation and not is_categorical:
            legend_kwds["orientation"] = orientation

        return legend, is_categorical, legend_kwds

    def _setup_geospatial_cax(self, engine: 'PlotEngine', use_divider: bool, column: Optional[str], legend: bool,
                              orientation: Optional[str]) -> Any:
        cax = None
        if use_divider and column and legend:
            try:
                divider = make_axes_locatable(engine.current_ax)
                if orientation == "horizontal":
                    cax = divider.append_axes("bottom", size="5%", pad=0.1)
                else:
                    cax = divider.append_axes("right", size="5%", pad=0.1)

                engine.current_ax._cax = cax
            except Exception as DividerError:
                print(f"Error creating axis divider: {DividerError}")

        return cax

    def _add_geospatial_basemap(self, engine: 'PlotEngine', gdf: Any, add_basemap: bool, basemap_source: str,
                                basemap_zoom: Any) -> None:
        if add_basemap and ctx:
            try:
                provider = ctx.providers.OpenStreetMap.Mapnik
                source_map = {
                    "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
                    "CartoDB Positron": ctx.providers.CartoDB.Positron,
                    "CartoDB DarkMatter": ctx.providers.CartoDB.DarkMatter,
                    "Esri Satellite": ctx.providers.Esri.WorldImagery,
                    "Esri Street": ctx.providers.Esri.WorldStreetMap
                }
                if basemap_source in source_map:
                    provider = source_map[basemap_source]
                if gdf.crs:
                    ctx.add_basemap(
                        engine.current_ax,
                        crs=gdf.crs.to_string(),
                        source=provider,
                        zoom=basemap_zoom
                    )
                else:
                    print("Unable to add basemap: CRS is undefined")
            except Exception as BaseMapError:
                print(f"Failed to add basemap: {BaseMapError}")
        elif add_basemap and not ctx:
            engine.current_ax.text(0.02, 0.02, "Install contextily for basemap support",
                                   transform=engine.current_ax.transAxes, fontsize=8, color="red",
                                   bbox=dict(facecolor="white", alpha=0.7))

    def execute(self, engine: 'PlotEngine', plot_tab: 'PlotTab', x_col: str, y_cols: List[str], axes_flipped: bool,
                font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        if gpd is None:
            if hasattr(plot_tab, "status_bar"):
                plot_tab.status_bar.log("GeoPandas library not found. Please install it.", "WARNING")
            return "GeoPandas library not found. Please install it first (`pip install geopandas`) to use geospatial plotting functions."

        df = plot_tab.data_handler.df
        engine._clear_axes()

        if "geometry" not in df.columns:
            return "DataFrame does not contain a 'geometry' column needed to create a geospatial plot."

        try:
            gdf = gpd.GeoDataFrame(df, geometry="geometry")
        except Exception as LoadGeoDataFrameError:
            return f"Failed to create GeoDataFrame: {str(LoadGeoDataFrameError)}"

        plot_col = y_cols[0] if y_cols else None

        title = general_kwargs.pop("title", None)
        xlabel = general_kwargs.pop("xlabel", None)
        ylabel = general_kwargs.pop("ylabel", None)
        legend = general_kwargs.pop("legend", True)
        cmap_name = general_kwargs.pop("cmap", general_kwargs.pop("palette", None))

        orientation = "vertical"
        use_divider = False
        axis_off = False

        if hasattr(plot_tab, "geo_legend_loc_combo"):
            orientation = plot_tab.geo_legend_loc_combo.currentText()
        if hasattr(plot_tab, "geo_use_divider_check"):
            use_divider = plot_tab.geo_use_divider_check.isChecked()
        if hasattr(plot_tab, "geo_axis_off_check"):
            axis_off = plot_tab.geo_axis_off_check.isChecked()

        kwargs = plot_kwargs.copy()

        if plot_col:
            kwargs["column"] = plot_col

        if hasattr(plot_tab, "geo_scheme_combo"):
            scheme = plot_tab.geo_scheme_combo.currentText()
            if plot_col and scheme != "None":
                kwargs["scheme"] = scheme
                if hasattr(plot_tab, "geo_k_spin"):
                    kwargs["k"] = plot_tab.geo_k_spin.value()

        if hasattr(plot_tab, "geo_edge_color"):
            kwargs["edgecolor"] = plot_tab.geo_edge_color
        if hasattr(plot_tab, "geo_linewidth_spin"):
            kwargs["linewidth"] = plot_tab.geo_linewidth_spin.value()

        if hasattr(plot_tab, "geo_boundary_check") and plot_tab.geo_boundary_check.isChecked():
            kwargs["facecolor"] = "none"

        target_crs = general_kwargs.pop("target_crs", None)
        add_basemap = general_kwargs.pop("add_basemap", False)
        basemap_source = general_kwargs.pop("basemap_source", "OpenStreetMap")
        basemap_zoom = general_kwargs.pop("basemap_zoom", "auto")

        gdf = self._handle_geospatial_crs(gdf, target_crs, add_basemap)
        legend_kwds = general_kwargs.pop("legend_kwds", {})

        legend, is_categorical, legend_kwds = self._configure_geospatial_legend(gdf, plot_col, legend, orientation,
                                                                                legend_kwds, use_divider, kwargs)
        cax = self._setup_geospatial_cax(engine, use_divider, plot_col, legend, orientation)

        if cmap_name and not is_categorical:
            kwargs["cmap"] = cmap_name
        elif "cmap" not in kwargs and not is_categorical:
            kwargs["cmap"] = "viridis"

        if plot_col and plot_col in gdf:
            gdf.plot(column=plot_col, ax=engine.current_ax, cax=cax, legend=legend, legend_kwds=legend_kwds, **kwargs)
        else:
            kwargs.pop("cmap", None)
            gdf.plot(ax=engine.current_ax, **kwargs)

        if axis_off:
            engine.current_ax.set_axis_off()

        self._add_geospatial_basemap(engine, gdf, add_basemap, basemap_source, basemap_zoom)
        engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)

        return None