# core/plot_engine.py
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib
import pandas as pd
import numpy as np
import seaborn as sns
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from core.regression_analyser import RegressionMetrics
from ui.status_bar import LogLevel

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
try:
    import geopandas as gpd
    from mpl_toolkits.axes_grid1 import make_axes_locatable
except ImportError:
    gpd = None
try:
    import contextily as ctx
except ImportError:
    ctx = None



class PlotEngine:
    """Manages all plotting functionality"""
    
    AVAILABLE_PLOTS = {
        'Line': 'plot_line',
        'Scatter': 'plot_scatter',
        'Bar': 'plot_bar',
        'Histogram': 'plot_histogram',
        'Box': 'plot_box',
        'Violin': 'plot_violin',
        'Heatmap': 'plot_heatmap',
        'KDE': 'plot_kde',
        'Area': 'plot_area',
        'Pie': 'plot_pie',
        'Count Plot': 'plot_count',
        'Hexbin': 'plot_hexbin',
        '2D Density': 'plot_density_2d',
        "Stem": "plot_stem",
        "Stackplot": "plot_stackplot",
        "Stairs": "plot_stairs",
        "Eventplot": "plot_eventplot",
        "ECDF": "plot_ecdf",
        "2D Histogram": "plot_hist2d",
        "Image Show (imshow)": "plot_imshow",
        "pcolormesh": "plot_pcolormesh",
        "Contour": "plot_contour",
        "Contourf": "plot_contourf",
        "Barbs": "plot_barbs",
        "Quiver": "plot_quiver",
        "Streamplot": "plot_streamplot",
        "Tricontour": "plot_tricontour",
        "Tricontourf": "plot_tricontourf",
        "Tripcolor": "plot_tripcolor",
        "Triplot": "plot_triplot",
        "GeoSpatial": "plot_geospatial",
        "3D Scatter": "plot_scatter_3d",
        "3D Line": "plot_line_3d",
        "3D Surface": "plot_surface_3d",
    }
    
    PLOT_DESCRIPTIONS: Dict[str, str] = {
        "Line": "A line chart is a type of graph that displays information as a series of data points connected by straight line segments. It is commonly used to visualize trends and changes in data over continuous intervals, such as time. The horizontal axis (x-axis) typically represents a sequential progression (e.g., time), and the vertical axis (y-axis) shows a quantitative value.",

        "Scatter":"A scatter plot is a graph that uses dots to represent the values of two different numeric variables, showing the relationship between them. Each dot's position on the horizontal (x-axis) and vertical (y-axis) indicates the values for an individual data point. Scatter plots are used to observe patterns, trends, and correlations between variables, such as determining if an increase in one variable corresponds with an increase or decrease in another. ",

        "Bar": "A bar chart is a data visualization tool that uses rectangular bars to represent categorical data, with the length or height of the bars proportional to the values they represent. It is used to compare different categories and show variations in data, making it useful for visualizing things like sales figures, survey responses, or monthly rainfall. Bar charts can be oriented vertically or horizontally and can display one or more sets of data.",

        "Histogram":"A histogram is a graphical representation of the distribution of a set of numerical data. It uses bars to show the frequency of data points that fall into specific, consecutive ranges or 'bins'. The height of each bar indicates the number of data points in that bin, making it useful for visualizing the shape, center, and spread of the data.",

        "Box": "A box plot is a graphical tool that visualizes the distribution of numerical data through its quartiles, providing a five-number summary: minimum, first quartile ((Q_{1})), median, third quartile ((Q_{3})), and maximum. It uses a box to represent the middle 50%  of the data (the interquartile range, or (IQR)), with a line inside for the median. 'Whiskers' extend from the box to the minimum and maximum values, and outliers may be shown as individual points beyond the whiskers.",

        "Violin": "A violin plot is a statistical visualization that combines a box plot with a kernel density plot to show the distribution of a numeric variable for one or more groups. The plot's shape is determined by the data density—it is wider where values are more frequent and narrower where they are less frequent, providing a visual representation of peaks in the data. Inside the violin shape, a miniature box plot can be included to display summary statistics like the median and interquartile range.",

        "Heatmap": "A heatmap is a data visualization technique that uses color to represent the magnitude of a variable, making complex data easier to interpret. It typically displays data as a grid of colored squares, where the intensity or shade of the color corresponds to the data's value, ranging from 'cool' (low values) to 'hot' (high values). Common uses include showing user behavior on websites, such as clicks and scroll depth, as well as representing geographical or statistical data like population density or temperature variations.",

        "KDE": "A kernel density estimation (KDE) plot is a visualization that creates a smooth curve to show the distribution of a continuous variable, acting as a smoothed-out version of a histogram. It is a non-parametric way to estimate the probability density function (PDF) of the data, helping to identify patterns, trends, and outliers in a clearer, more continuous way than with a histogram.",

        "Area": "An area chart is a type of line chart that shows quantitative data over time by filling the space between the plotted line and the axis with color or shading. It is used to emphasize the volume or magnitude of change over time, and can also be used to show how different data series contribute to a total.",

        "Pie": "A pie chart is a circular graphic that represents parts of a whole, with each 'slice' of the pie showing the proportional size of a category. The slices are proportional to the quantities they represent, and all slices combined make up the whole, typically equaling 100%.",

        "Count Plot": "A count plot can be thought of as a histogram across a categorical, instead of quantitative, variable. The basic API and options are identical to those for barplot(), so you can compare counts across nested variables.",

        "Hexbin": "A hexbin plot is a type of 2D histogram that represents the density of data points in a scatter plot by dividing the graphing area into hexagonal bins. Instead of showing individual points, it uses a color gradient to show how many data points fall into each hexagon, making it useful for visualizing large datasets where points would otherwise overlap.",

        "2D Density": "A 2D density plot visualizes the relationship between two numeric variables by showing the concentration of data points in a 2D space. It uses a color gradient to represent areas with a high density of points, making it useful for identifying patterns in large datasets where a scatterplot would result in overplotting. Common types include 2D histograms with squares or hexagons and contour plots.",
        "Stem": "A stem plot draws vertical lines at each x-position to a y-value, with a marker at the top. It is excellent for visualizing discrete time series or categorical data points.",
        "Stackplot": "A stackplot (or stacked area chart) visualizes the contribution of different groups to a whole over time or another continuous variable. Each colored area represents one group, and the areas are stacked on top of each other.",
        "Stairs": "A stairs plot creates a step-like visualization, similar to a line plot but with vertical and horizontal lines only (no diagonals). It's useful for displaying data that changes at discrete intervals.",
        "Eventplot": "An eventplot visualizes identical-looking objects (e.g., lines) at different positions. It's commonly used for plotting spike trains or other event-based data, where the position on one axis represents the time or location of an event.",
        "ECDF": "An Empirical Cumulative Distribution Function (ECDF) plot shows the proportion of data points that are less than or equal to a given value. It's a step function that provides a clear visual of the data's distribution.",
        "2D Histogram": "A 2D histogram (hist2d) bins the data into 2D rectangles and uses color to represent the number of data points in each bin. It is excellent for visualizing the joint distribution of two variables with a large number of points.",
        "Image Show (imshow)": "Displays data as an image, where the data is represented by colors. This is used for visualizing 2D arrays or matrices, such as a correlation matrix. Requires data to be in a 2D grid format (use X, Y-pos, and Z-value).",
        "pcolormesh": "Creates a pseudocolor plot of a 2D array. It's highly efficient for plotting large arrays and is often used for 2D histograms or other gridded data. Requires data to be in a 2D grid format (use X, Y-pos, and Z-value).",
        "Contour": "A contour plot displays 3D data in 2D by showing lines (contours) that connect points of equal value (like a topographical map). It requires data to be in a 2D grid (use X, Y-pos, and Z-value).",
        "Contourf": "A filled contour plot (contourf) is similar to a contour plot but fills the areas between the contour lines with colors. Requires data to be in a 2D grid (use X, Y-pos, and Z-value).",
        "Barbs": "A barb plot is used to visualize vector fields, typically in meteorology to show wind direction and speed. Requires X, Y-position and U, V vector components (4 columns).",
        "Quiver": "A quiver plot displays a 2D field of arrows. Each arrow represents a vector at a specific (x, y) point. Requires X, Y-position and U, V vector components (4 columns).",
        "Streamplot": "A streamplot visualizes a 2D vector field by drawing streamlines. It's excellent for understanding the flow of a vector field. Requires gridded X, Y-position and U, V vector components (4 columns).",
        "Tricontour": "A triangular contour plot. Similar to a regular contour plot, but it works on an unstructured grid of (x, y, z) data points by first creating a triangulation.",
        "Tricontourf": "A filled triangular contour plot. Like `contourf`, it fills the areas between the contour lines generated from an unstructured (x, y, z) dataset.",
        "Tripcolor": "Creates a pseudocolor plot from an unstructured (x, y, z) dataset. It triangulates the (x, y) points and colors each triangle based on its Z value.",
        "Triplot": "A simple plot that draws the underlying triangulation of an (x, y) dataset, showing the network of triangles used for other tri-plots.",
        "GeoSpatial": "Visualizes geospatial data using GeoPandas. Requires a GeoDataFrame (imported from .shp, .geojson, etc.). The 'X Column' can be used to select a column for choropleth coloring (values determine color).",
        "3D Scatter": "A 3D scatter plot visualizes data points in a three-dimensional space. Requires X, Y, and Z columns mapped to respective dimensions.",
        "3D Line": "A 3D line plot connects data points in a three-dimensional sequence. Requires X, Y, and Z columns.",
        "3D Surface": "A 3D surface plot visualizes gridded data as a continuous surface. Requires X, Y, and Z columns mapped to a 2D grid."
    }

    def __init__(self):
        self.current_figure: Optional[Figure] = None
        self.current_ax = None
        self.axes_flat = []
        self.current_plot_type: Optional[str] = None
        self.plot_config: Dict[str, Any] = {}
        self.secondary_ax = None
        self._cached_processed_data: Optional[pd.DataFrame] = None
        self._is_data_dirty: bool = False
    
    def cache_data(self, df: pd.DataFrame) -> None:
        self._cached_processed_data = df.copy() if df is not None else None
        self._is_data_dirty = False
        
    def get_cached_data(self) -> Optional[pd.DataFrame]:
        return self._cached_processed_data
    
    def create_figure(self, figsize=(10, 6), dpi=100) -> Figure:
        """Create a new matplotlib figure"""
        # Closing the previous figure to prevent references to past figures.
        if self.current_figure is not None:
            plt.close(self.current_figure)
        self.current_figure = Figure(figsize=figsize, dpi=dpi)
        self.setup_layout(1, 1)
        return self.current_figure

    def _set_labels(self, title: Optional[str], xlabel: Optional[str], ylabel: Optional[str], legend: bool, **kwargs) -> None:
        """Function that sets labels and handles latex rendering if requqested"""
        usetex = kwargs.get("usetex", False)

        plt.rcParams["text.usetex"] = usetex

        default_weight = "normal" if usetex else "bold"
        title_weight = kwargs.get("title_weight", default_weight)

        if title:
            self.current_ax.set_title(title, fontsize=14, fontweight=title_weight, picker=True)
        if xlabel:
            self.current_ax.set_xlabel(xlabel, fontsize=12, picker=True)
        if ylabel:
            self.current_ax.set_ylabel(ylabel, fontsize=12, picker=True)
        
        zlabel = kwargs.get("zlabel", None)
        if zlabel and hasattr(self.current_ax, "set_zlabel"):
            self.current_ax.set_zlabel(zlabel, fontsize=12, picker=True)
        
        if legend:
            self.current_ax.legend()
    
    def finalize_layout(self) -> None:
        if self.current_figure is not None:
            self.current_figure.tight_layout()

    def setup_layout(self, rows: int = 1, cols: int = 1, sharex: bool = False, sharey: bool = False, custom_grid: Optional[List[Tuple[int, int, int, int]]] = None) -> None:
        """Subplot layout grid"""
        if self.current_figure is None:
            return
        
        self.current_figure.clear()
        
        self._sharex = sharex
        self._sharey = sharey
        
        if custom_grid:
            self.axes_flat = []
            grid_spec = self.current_figure.add_gridspec(rows, cols)
            base_ax_x = None
            base_ax_y = None
            
            for index, (r_start, r_end, c_start, c_end) in enumerate(custom_grid):
                subplot_kwargs: Dict[str, Any] = {}
                if sharex and base_ax_x is not None:
                    subplot_kwargs["sharex"] = base_ax_x
                if sharey and base_ax_y is not None:
                    subplot_kwargs["sharey"] = base_ax_y
                    
                ax = self.current_figure.add_subplot(grid_spec[r_start:r_end, c_start:c_end], **subplot_kwargs)
                self.axes_flat.append(ax)
                
                if index == 0:
                    base_ax_x = ax
                    base_ax_y = ax
        else:
            axes = self.current_figure.subplots(rows, cols, sharex=sharex, sharey=sharey)
            if isinstance(axes, np.ndarray):
                self.axes_flat = axes.flatten().tolist()
            else:
                self.axes_flat = [axes]
        
        if self.axes_flat:
            self.current_ax = self.axes_flat[0]
            
            if sharex or sharey:
                for ax in self.axes_flat:
                    ax.label_outer()
            
        self.current_figure.tight_layout()

    def set_active_subplot(self, index: int):
        """Set the active subplot"""
        if 0 <= index < len(self.axes_flat):
            self.current_ax = self.axes_flat[index]
        
    def clear_current_axis(self):
        """Clear the active subplot"""
        if self.current_ax:
            if hasattr(self.current_ax, "_cbar_obj") and self.current_ax._cbar_obj is not None:
                try:
                    self.current_ax._cbar_obj.remove()
                except Exception:
                    pass
                self.current_ax._cbar_obj = None
            if hasattr(self.current_ax, "_cax") and self.current_ax._cax is not None:
                try:
                    if self.current_figure:
                        self.current_figure.delaxes(self.current_ax._cax)
                    else:
                        self.current_ax._cax.remove()
                except Exception:
                    pass
                self.current_ax._cax = None
            
            self.current_ax.set_axes_locator(None)
            self.current_ax.clear()
    
    def get_active_axis_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """Function to calculate Qt geometry for the active axis relative to the current canvas"""
        if not self.current_ax or not self.current_figure:
            return None
        
        # We get the device pixel ratio for scaling on higher DPI screens
        dpr = 1.0
        canvas = self.current_figure.canvas
        if canvas and hasattr(canvas, "devicePixelRatio"):
            dpr = canvas.devicePixelRatio()
        
        try:
            trans = self.current_ax.transAxes
            p0 = trans.transform([0, 0])
            p1 = trans.transform([1, 1])

            x0, y0 = p0
            x1, y1 = p1

            fig_height_px = self.current_figure.bbox.height

            px_x = x0
            px_y = fig_height_px - y1
            px_w = x1 - x0
            px_h = y1 - y0

            x = px_x / dpr
            y = px_y / dpr
            w = px_w / dpr
            h = px_h / dpr

        except Exception:
            bbox = self.current_ax.get_position()
            width_in, height_in = self.current_figure.get_size_inches()
            dpi = self.current_figure.get_dpi()

            fig_width_px = width_in * dpi
            fig_height_px = height_in * dpi

            px_x = bbox.x0 * fig_width_px
            px_w = bbox.width * fig_width_px
            px_h = bbox.height * fig_height_px
            px_y = fig_height_px - (bbox.y1 * fig_height_px)

            x = px_x / dpr
            y = px_y / dpr
            w = px_w / dpr
            h = px_h / dpr

        if canvas:
            from PyQt6.QtCore import QPointF
            global_pos = canvas.mapToGlobal(QPointF(x, y).toPoint())
            x, y = global_pos.x(), global_pos.y()

        return (int(x), int(y), int(w), int(h))
    
    def _get_colors_from_cmap(self, cmap_name, n_colors):
        """Generate a list of colors from a cmap"""
        if not cmap_name:
            return None
        
        try:
            cmap = matplotlib.colormaps[cmap_name]
            return [cmap(i) for i in np.linspace(0, 1, n_colors)]
        except KeyError:
            return None
    
    def _clear_axes(self):
        if self.secondary_ax:
            try:
                self.secondary_ax.remove()
            except Exception:
                pass
            self.secondary_ax = None
        if hasattr(self.current_ax, "_cbar_obj") and self.current_ax._cbar_obj is not None:
            try:
                self.current_ax._cbar_obj.remove()
            except Exception:
                pass
            self.current_ax._cbar_obj = None
        
        if hasattr(self.current_ax, "_cax") and self.current_ax._cax is not None:
            try:
                if self.current_figure:
                    self.current_figure.delaxes(self.current_ax._cax)
                else:
                    self.current_ax._cax.remove()
            except Exception:
                pass
            self.current_ax._cax = None
        
        for coll in self.current_ax.collections:
            if hasattr(coll, "colorbar") and coll.colorbar is not None:
                try:
                    coll.colorbar.remove()
                except Exception:
                    pass
        
        for img in self.current_ax.images:
            if hasattr(img, "colorbar") and img.colobar is not None:
                try:
                    img.colorbar.remove()
                except Exception:
                    pass
        
        self.current_ax.clear()
        
        if getattr(self, '_sharex', False) or getattr(self, '_sharey', False):
            for ax in self.axes_flat:
                ax.label_outer()
    
    def _handle_secondary_axis(self, df: pd.DataFrame, x: str, secondary_y: str, secondary_plot_type: str, **kwargs) -> Any:
        """
        Method to handle plotting data on a secondary y axis (TwinX)
        Returns the secondary axis objet
        """
        if not secondary_y or secondary_y not in df.columns:
            return None
        
        horizontal = kwargs.get("horizontal", False)
        if horizontal:
            # for horizontal we create a new x-axis
            ax2 = self.current_ax.twiny()
            self.secondary_ax = ax2
            
            if secondary_plot_type == "Line":
                ax2.plot(df[secondary_y], df[x], label=f"{secondary_y}")
            elif secondary_plot_type == "Bar":
                ax2.barh(df[x], df[secondary_y], label=f"{secondary_y}")
            elif secondary_plot_type == "Scatter":
                ax2.scatter(df[secondary_y], df[x], label=f"{secondary_y}")
            elif secondary_plot_type == "Area":
                ax2.fill_between(df[x], 0, df[secondary_y], label=f"{secondary_y}")
            else:
                ax2.plot(df[secondary_y], df[x], label=f"{secondary_y}")
            
            ax2.set_xlabel(secondary_y)
            ax2.tick_params(axis="x")
        else:
            ax2 = self.current_ax.twinx()
            self.secondary_ax = ax2

            if secondary_plot_type == "Line":
                ax2.plot(df[x], df[secondary_y], label=f"{secondary_y}")
            elif secondary_plot_type == "Bar":
                ax2.bar(df[x], df[secondary_y], label=f"{secondary_y}")
            elif secondary_plot_type == "Scatter":
                ax2.scatter(df[x], df[secondary_y], label=f"{secondary_y}")
            elif secondary_plot_type == "Area":
                ax2.fill_between(df[x], 0, df[secondary_y], label=f"{secondary_y}")
            else:
                ax2.plot(df[x], df[secondary_y], label=f"{secondary_y}")
            
            ax2.set_ylabel(secondary_y)
            ax2.tick_params(axis="y")
        
        return ax2

    def _consolidate_legends(self, ax1, ax2):
        """Combine legends from primary and secondary axes into one"""
        if not ax1 and ax2:
            return
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()

        if lines1 or lines2:
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")
    
    def plot_line(self, df: pd.DataFrame, x: str, y: List[str], **kwargs) -> None:
        """Create a line plot"""
        self._clear_axes()
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        hue = kwargs.pop("hue", None)
        cmap_name = kwargs.pop("cmap", None)
        secondary_y = kwargs.pop("secondary_y", None)
        secondary_plot_type = kwargs.pop("secondary_plot_type", "Line")

        marker = kwargs.pop("marker", None)

        if marker in (None, ""):
            kwargs["marker"] = None
        elif marker is not None:
            kwargs["marker"] = marker

        if hue:
            groups = df[hue].unique()
            colors = self._get_colors_from_cmap(cmap_name, len(groups))

            for i, group in enumerate(groups):
                mask = (df[hue] == group) & df[x].notna()
                if colors: kwargs["color"] = colors[i]
                for col in y:
                    self.current_ax.plot(df.loc[mask, x], df.loc[mask, col], label=f"{col} - {group}", picker=5, **kwargs)
        else:
            colors = self._get_colors_from_cmap(cmap_name, len(y))
            for i, col in enumerate(y):
                mask = df[x].notna()
                if colors: kwargs["color"] = colors[i]
                self.current_ax.plot(df.loc[mask, x], df.loc[mask, col], label=col, picker=5, **kwargs)
        
        ax2 = None
        if secondary_y:
            ax2 = self._handle_secondary_axis(df, x, secondary_y, secondary_plot_type, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

        if legend:
            if ax2:
                self._consolidate_legends(self.current_ax, ax2)
            else:
                self.current_ax.legend()
    
    def plot_scatter(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a scatter plot"""
        self._clear_axes()
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        hue = kwargs.pop('hue', None)
        cmap_name = kwargs.pop("cmap", None)
        secondary_y = kwargs.pop("secondary_y", None)
        secondary_plot_type = kwargs.pop("secondary_plot_type", "Line")
        
        size_col = kwargs.pop("size", None)
        size_min = kwargs.pop("size_min", 30)
        size_max = kwargs.pop("size_max", 500)
        
        s_min_global, s_max_global = 0.0, 0.0
        if size_col and size_col in df.columns:
            s_min_global, s_max_global = df[size_col].min(), df[size_col].max()
        
        if hue:
            groups = df[hue].unique()
            colors = self._get_colors_from_cmap(cmap_name, len(groups))
            
            for i, group in enumerate(groups):
                mask = (df[hue] == group) & df[x].notna() & df[y].notna()
                if colors: kwargs["color"] = colors[i]
                
                if size_col and size_col in df.columns:
                    s_data = df.loc[mask, size_col]
                    if s_min_global == s_max_global or pd.isna(s_min_global):
                        kwargs["s"] = size_min
                    else:
                        kwargs["s"] = size_min + (size_max - size_min) * (s_data - s_min_global) / (s_max_global - s_min_global)
                        
                self.current_ax.scatter(df.loc[mask, x], df.loc[mask, y], label=group, picker=5, **kwargs)
        else:
            if cmap_name: kwargs["cmap"] = cmap_name
            mask = df[x].notna() & df[y].notna()
            
            if size_col and size_col in df.columns:
                s_data = df.loc[mask, size_col]
                if s_min_global == s_max_global or pd.isna(s_min_global):
                    kwargs["s"] = size_min
                else:
                    kwargs["s"] = size_min + (size_max - size_min) * (s_data - s_min_global) / (s_max_global - s_min_global)
                    
            self.current_ax.scatter(df.loc[mask, x], df.loc[mask, y], picker=5, **kwargs)
        
        ax2 = None
        if secondary_y:
            ax2 = self._handle_secondary_axis(df, x, secondary_y, secondary_plot_type, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

        if legend:
            if ax2:
                self._consolidate_legends(self.current_ax, ax2)
            else:
                handles, labels = self.current_ax.get_legend_handles_labels()
                
                if size_col and size_col in df.columns and s_min_global != s_max_global:
                    if not labels:
                        labels = []
                        
                    labels.append(f"{size_col} (Size)")
                    handles.append(self.current_ax.scatter([], [], s=0, color='none'))
                    
                    for val in np.linspace(s_min_global, s_max_global, 4):
                        marker_size = size_min + (size_max - size_min) * (val - s_min_global) / (s_max_global - s_min_global)
                        dummy = self.current_ax.scatter([], [], s=marker_size, color='gray', alpha=0.5)
                        
                        handles.append(dummy)
                        labels.append(f"{int(val)}" if float(val).is_integer() else f"{val:.2f}")
                        
                if handles:
                    self.current_ax.legend(handles, labels)
    
    def plot_bar(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a bar plot"""
        self._clear_axes()
        df = df[df[x].notna()]
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        hue = kwargs.pop('hue', None)
        width = kwargs.pop("width", 0.8)
        horizontal = kwargs.pop("horizontal", False)
        palette = kwargs.pop("palette", None)
        secondary_y = kwargs.pop("secondary_y", None)
        secondary_plot_type = kwargs.pop("secondary_plot_type", "Line")
        
        if isinstance(y, str):
            y = [y]

        if len(y) == 1 and not hue:
            #single y col
            y_col_name = y[0]
            if horizontal:
                self.current_ax.barh(df[x], df[y_col_name], height=width, picker=True, **kwargs)
            else:
                self.current_ax.bar(df[x], df[y_col_name], width=width, picker=True, **kwargs)
        
        elif len(y) > 1:
            #grouped bar chart
            x_labels = df[x].unique()
            x_pos = np.arange(len(x_labels))
            bar_width = width / len(y)
            
            colors = self._get_colors_from_cmap(palette, len(y))

            for i, col in enumerate(y):
                offset = (i - len(y) / 2) * bar_width + bar_width / 2
                values = [df[df[x] == label][col].values[0] if len(df[df[x] == label]) > 0 else 0 for label in x_labels]
                
                if colors: kwargs["color"] = colors[i]

                if horizontal:
                    self.current_ax.barh(x_pos + offset, values, height=bar_width, label=col, picker=True, **kwargs)
                else:
                    self.current_ax.bar(x_pos + offset, values, width=bar_width, label=col, picker=True, **kwargs)
            
            if horizontal:
                self._helper_format_categorical_axis(self.current_ax.yaxis, x_labels)
            else:
                self._helper_format_categorical_axis(self.current_ax.xaxis, x_labels)
        
        elif hue:
            # Single y with hue using seaborn
            import seaborn as sns
            if palette: kwargs["palette"] = palette
            
            if horizontal:
                sns.barplot(data=df, y=x, x=y[0], hue=hue, ax=self.current_ax, orient="h", picker=True, **kwargs)
            else:
                sns.barplot(data=df, x=x, y=y[0], hue=hue, ax=self.current_ax, picker=True, **kwargs)
        
        ax2 = None
        if secondary_y:
            ax2 = self._handle_secondary_axis(df, x, secondary_y, secondary_plot_type, horizontal=horizontal, **kwargs)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)

        if legend:
            if ax2:
                self._consolidate_legends(self.current_ax, ax2)
            else:
                handles, labels = self.current_ax.get_legend_handles_labels()
                if handles:
                    self.current_ax.legend()
    
    def plot_histogram(self, df: pd.DataFrame, column: str, **kwargs) -> None:
        """Create a histogram"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        bins = kwargs.pop('bins', 30)
        show_normal = kwargs.pop("show_normal", False)
        show_kde = kwargs.pop("show_kde", False)
        show_stats = kwargs.pop("show_stats", True)
        cmap_name = kwargs.pop("cmap", None)
        hue = kwargs.pop("hue", None)
        
        if hue and hue in df.columns:
            groups = df[hue].dropna().unique()
            data_list = []
            labels = []
            for group in groups:
                group_data = df[df[hue] == group][column].dropna()
                if not group_data.empty:
                    data_list.append(group_data)
                    labels.append(str(group))
            plot_data = data_list
            colors = self._get_colors_from_cmap(cmap_name, len(data_list))
            if colors:
                kwargs["color"] = colors
            kwargs["label"] = labels
        else:
            plot_data = df[column].dropna()
        n, bins_edges, patches = self.current_ax.hist(
            plot_data, bins=bins, density=show_normal or show_kde, picker=True, **kwargs
        )
        if hue and hue in df.columns:
            for i, group_data in enumerate(data_list):
                c = colors[i] if colors else None
                if show_normal:
                    from scipy.stats import norm
                    mu, sigma = group_data.mean(), group_data.std()
                    if sigma > 0:
                        x = np.linspace(group_data.min(), group_data.max(), 100)
                        normal_curve = norm.pdf(x, mu, sigma)
                        self.current_ax.plot(x, normal_curve, color=c, linestyle="-", linewidth=2, label=f"Norm ({labels[i]})")
                if show_kde:
                    from scipy.stats import gaussian_kde
                    try:
                        kde = gaussian_kde(group_data)
                        x = np.linspace(group_data.min(), group_data.max(), 100)
                        kde_curve = kde(x)
                        self.current_ax.plot(x, kde_curve, color=c, linestyle="--", linewidth=2, label=f"KDE ({labels[i]})")
                    except Exception:
                        pass
            if legend or show_normal or show_kde:
                self.current_ax.legend()
        else:
            data = plot_data
            mu = data.mean()
            sigma = data.std()
            median = data.median()

            if show_normal and sigma > 0:
                from scipy.stats import norm
                x = np.linspace(data.min(), data.max(), 100)
                normal_curve = norm.pdf(x, mu, sigma)
                self.current_ax.plot(x, normal_curve, "r-", linewidth=2.5, label=f"Normal (µ={mu:.2f}, σ={sigma:.2f})")
            
            if show_kde:
                from scipy.stats import gaussian_kde
                try:
                    kde = gaussian_kde(data)
                    x = np.linspace(data.min(), data.max(), 100)
                    kde_curve = kde(x)
                    self.current_ax.plot(x, kde_curve, "g-", linewidth=2.5, label="KDE")
                except Exception:
                    pass

            if show_normal or show_kde:
                self.current_ax.legend()
            
            # Add some statistics for single plots
            if show_stats and (show_normal or show_kde):
                stats_text = f"µ = {mu:.3f}\nσ = {sigma:.3f}\nmedian = {median:.3f}\nn = {len(data)}"
                props = dict(boxstyle="round", facecolor="wheat", alpha=0.85, edgecolor="black", linewidth=1)
                self.current_ax.text(0.75, 0.95, stats_text, transform=self.current_ax.transAxes, fontsize=10, verticalalignment="top", bbox=props, fontfamily="monospace")

        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_box(self, df: pd.DataFrame, columns: List[str], **kwargs) -> None:
        """Create a box plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)

        if isinstance(columns, str):
            columns = [columns]
        
        df[columns].plot(kind='box', ax=self.current_ax, picker=True, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_violin(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a violin plot using seaborn"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        
        sns.violinplot(data=df, x=x, y=y, ax=self.current_ax, picker=True, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_heatmap(self, df: pd.DataFrame, x: Optional[str] = None, y: Optional[str] = None, z: Optional[str] = None, **kwargs) -> None:
        """Create a heatmap using seaborn"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        
        valid_x = x and x in df.columns
        valid_y = y and y in df.columns
        valid_z = z and z in df.columns
        
        cbar_kws = kwargs.pop("cbar_kws", {})
        
        if valid_x and valid_y:
            if valid_z:
                plot_data = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
            else:
                plot_data = pd.crosstab(df[y], df[x])
            sns.heatmap(plot_data, annot=True, ax=self.current_ax, cbar=False, picker=True, **kwargs)
            if xlabel is None:
                xlabel = x
            if ylabel is None:
                ylabel = y
        else:
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.empty:
                raise ValueError("No numeric columns available")
            sns.heatmap(numeric_df.corr(), annot=True, ax=self.current_ax, cbar=False, picker=True, **kwargs)
        
        if self.current_ax.collections:
            cb = self.current_figure.colorbar(self.current_ax.collections[0], ax=self.current_ax, **cbar_kws)
            self.current_ax._cbar_obj = cb
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_kde(self, df: pd.DataFrame, column: str, **kwargs) -> None:
        """Create a KDE plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        
        df[column].plot(kind='kde', ax=self.current_ax, picker=True, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_area(self, df: pd.DataFrame, x: str, y: List[str], **kwargs) -> None:
        """Create an area plot"""
        self._clear_axes()
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        secondary_y = kwargs.pop("secondary_y", None)
        secondary_plot_type = kwargs.pop("secondary_plot_type", "Line")

        if isinstance(y, str):
            y = [y]
        
        df_plot = df[df[x].notna()].set_index(x)[y]
        df_plot.plot(kind="area", ax=self.current_ax, stacked=True, picker=True, **kwargs)
        
        ax2 = None
        if secondary_y:
            ax2 = self._handle_secondary_axis(df, x, secondary_y, secondary_plot_type, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

        if legend:
            if ax2:
                self._consolidate_legends(self.current_ax, ax2)
            else:
                self.current_ax.legend()
    
    def plot_pie(self, df: pd.DataFrame, values: str, names: str, **kwargs) -> None:
        """Create a pie chart"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        show_percentages = kwargs.pop("show_percentages", True)
        start_angle = kwargs.pop("start_angle", 0)
        explode_first = kwargs.pop("explode_first", False)
        explode_distance = kwargs.pop("explode_distance", 0.1)
        shadow = kwargs.pop("shadow", False)
        cmap = kwargs.pop("cmap", None)

        # create format
        autopct = "%1.2f%%" if show_percentages else None

        #explode
        explode = None
        if explode_first:
            explode = [explode_distance] + [0] * (len(df[values]) - 1)
        
        self.current_ax.pie(df[values], labels=df[names], autopct=autopct, startangle=start_angle, explode=explode, shadow=shadow, **kwargs)
        self.current_ax.set_ylabel('')

        self.current_ax.axis("equal")
        
        self._set_labels(title, None, None, False, **kwargs)
    
    def plot_count(self, df: pd.DataFrame, column: str, **kwargs) -> None:
        """Create a count plot using seaborn"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        
        sns.countplot(data=df, x=column, ax=self.current_ax, picker=True, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_hexbin(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a hexbin plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)
        gridsize = kwargs.pop('gridsize', 20)
        
        mask = df[x].notna() & df[y].notna()
        self.current_ax.hexbin(df.loc[mask, x], df.loc[mask, y], gridsize=gridsize, picker=True, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_density_2d(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a 2D density plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        legend = kwargs.pop('legend', True)

        # add defaults
        if "cmap" not in kwargs:
            kwargs["cmap"] = "viridis"
        if "levels" not in kwargs:
            kwargs["levels"] = 10
        if "thresh" not in kwargs:
            kwargs["thresh"] = 0.05
        
        mask = df[x].notna() & df[y].notna()
        clean_df = df.loc[mask]
        
        sns.kdeplot(data=clean_df, x=x, y=y, ax=self.current_ax, fill=True, picker=True, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_stem(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a stem plot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        legend = kwargs.pop("legend", False)

        line_style = kwargs.pop("linestyle", "-")
        line_width = kwargs.pop("linewidth", 1.5)
        marker = kwargs.pop("marker", "o")
        marker_size = kwargs.pop("markersize", 6)
        if "s" in kwargs:
            marker_size = kwargs.pop("s")
        
        color = kwargs.pop("color", "#1f77b4")
        if "c" in kwargs:
            color = kwargs.pop("c")
        
        alpha = kwargs.pop("alpha", 1.0)
        label = kwargs.pop("label", y)
        orientation = kwargs.pop("orientation", "vertical")
        bottom = kwargs.pop("bottom", 0)

        if orientation == "horizontal":
            markerline, stemlines, baseline = self.current_ax.stem(
                df[y], df[x],
                orientation="horizontal",
                bottom=bottom,
                label=label,
                picker=True
            )
        else:
            markerline, stemlines, baseline = self.current_ax.stem(
                df[x], df[y],
                orientation="vertical",
                bottom=bottom,
                label=label,
                picker=True
            )
        
        plt.setp(markerline, marker=marker, markersize=marker_size, color=color, alpha=alpha)
        plt.setp(stemlines, linestyle=line_style, linewidth=line_width, color=color, alpha=alpha)
        plt.setp(baseline, color="gray", linewidth=1, linestyle="-")

        self._set_labels(title, xlabel, ylabel, legend, **kwargs)
    
    def plot_stackplot(self, df: pd.DataFrame, x: str, y: List[str], **kwargs) -> None:
        """Create a stackplot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        legend = kwargs.pop("legend", True)

        df_sorted = df[df[x].notna()].sort_values(by=x)
        y_data = [df_sorted[col] for col in y]

        self.current_ax.stackplot(df_sorted[x], *y_data, labels=y, picker=True, **kwargs)

        self._set_labels(title, xlabel, ylabel, legend, **kwargs)

    def plot_stairs(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a stairs plot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        legend = kwargs.pop("legend", True)
        cmap = kwargs.pop("cmap", None)

        df_sorted = df[df[x].notna()].sort_values(by=x)
        self.current_ax.step(df_sorted[x], df_sorted[y], where="mid", picker=True, **kwargs)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_eventplot(self, df: pd.DataFrame, y: list[str], **kwargs) -> None:
        """Create an eventplot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        _ = kwargs.pop("legend", None)

        data_to_plot = [df[col].dropna().values for col in y]

        self.current_ax.eventplot(data_to_plot, picker=True, **kwargs)

        if len(y) > 1:
            self.current_ax.set_yticks(range(len(y)))
            self.current_ax.set_yticklabels(y)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_hist2d(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a 2D histogram"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        _ = kwargs.pop("legend", None)

        mask = df[x].notna() & df[y].notna()
        hist = self.current_ax.hist2d(df.loc[mask, x], df.loc[mask, y], picker=True, **kwargs)
        self.current_figure.colorbar(hist[3], ax=self.current_ax, label="counts")

        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_ecdf(self, df: pd.DataFrame, y: str, **kwargs) -> None:
        """Create an ECDF plot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        _ = kwargs.pop("legend", None)

        self.current_ax.ecdf(df[y], **kwargs)

        self._set_labels(title, xlabel, "ECDF", False, picker=True, **kwargs)

    def _prepare_gridded_data(self, df: pd.DataFrame, x: str, y: str, z: str):
        """Helper func to pivot data for gridded plots"""
        try:
            if df[[x, y]].duplicated().any():
                #agg by mean
                df_agg = df.groupby([x, y])[z].mean().reset_index()
            else:
                df_agg = df
            
            pivot_df = df_agg.pivot(index=y, columns=x, values=z)
            pivot_df = pivot_df.sort_index(axis=0).sort_index(axis=1)

            X = pivot_df.columns.values
            Y = pivot_df.index.values
            Z = pivot_df.values

            
            return X, Y, Z
        except Exception as GridDataError:
            raise ValueError(f"Data could not be pivoted into a 2D grid. Is the data gridded?: Error: {str(GridDataError)}")
    
    def plot_imshow(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create an imshow plot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        _ = kwargs.pop("legend", None)

        X, Y, Z = self._prepare_gridded_data(df, x, y, z)

        img = self.current_ax.imshow(Z, extent=[X.min(), X.max(), Y.min(), Y.max()], origin="lower", aspect="auto", **kwargs)
        self.current_figure.colorbar(img, ax=self.current_ax, label=z)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_pcolormesh(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a pcolormesh plot"""
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        _ = kwargs.pop("legend", None)

        X, Y, Z = self._prepare_gridded_data(df, x, y, z)
        X_grid, Y_grid = np.meshgrid(X, Y)

        mesh = self.current_ax.pcolormesh(X_grid, Y_grid, Z, **kwargs)
        self.current_figure.colorbar(mesh, ax=self.current_ax, label=z)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_contour(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a contour plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)

        X, Y, Z = self._prepare_gridded_data(df, x, y, z)
        X_grid, Y_grid = np.meshgrid(X, Y)

        cont = self.current_ax.contour(X_grid, Y_grid, Z, **kwargs)
        self.current_ax.clabel(cont, inline=True, fontsize=8)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_contourf(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a filled contour plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)

        X, Y, Z = self._prepare_gridded_data(df, x, y, z)
        X_grid, Y_grid = np.meshgrid(X, Y)

        contf = self.current_ax.contourf(X_grid, Y_grid, Z, **kwargs)
        self.current_figure.colorbar(contf, ax=self.current_ax, label=z)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_barbs(self, df: pd.DataFrame, x: str, y: str, u: str, v: str, **kwargs) -> None:
        """Create a barbs plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)

        self.current_ax.barbs(df[x], df[y], df[u], df[v], **kwargs)

        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_quiver(self, df: pd.DataFrame, x: str, y: str, u: str, v: str, **kwargs) -> None:
        """Create a quiver plot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)
        
        self.current_ax.quiver(df[x], df[y], df[u], df[v], **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_streamplot(self, df: pd.DataFrame, x: str, y: str, u: str, v: str, **kwargs) -> None:
        """Create a streamplot"""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)


        
        try:
            X, Y, U_grid = self._prepare_gridded_data(df, x, y, u)
            _, _, V_grid = self._prepare_gridded_data(df, x, y, v)
            X_grid, Y_grid = np.meshgrid(X, Y)
        except Exception as PlotStreamPlotError:
            raise ValueError(f"Streamplot requires gridded data (pivoted x, y, u, v). Error: {PlotStreamPlotError}")

        self.current_ax.streamplot(X_grid, Y_grid, U_grid, V_grid, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)
    
    def plot_tricontour(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a tricontour plot from unstructured x, y, z."""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)
        
        cont = self.current_ax.tricontour(df[x], df[y], df[z], **kwargs)
        self.current_ax.clabel(cont, inline=True, fontsize=8)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_tricontourf(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a filled tricontour plot from unstructured x, y, z."""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)
        
        contf = self.current_ax.tricontourf(df[x], df[y], df[z], **kwargs)
        self.current_figure.colorbar(contf, ax=self.current_ax, label=z)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_tripcolor(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a tripcolor plot from unstructured x, y, z."""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)
        
        trip = self.current_ax.tripcolor(df[x], df[y], df[z], **kwargs)
        self.current_figure.colorbar(trip, ax=self.current_ax, label=z)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def plot_triplot(self, df: pd.DataFrame, x: str, y: str, **kwargs) -> None:
        """Create a triplot from unstructured x, y."""
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        _ = kwargs.pop("legend", None)
        
        self.current_ax.triplot(df[x], df[y], **kwargs)
        
        self._set_labels(title, xlabel, ylabel, False, **kwargs)

    def add_table(self, df: pd.DataFrame, loc='bottom', auto_font_size=False, fontsize=10, scale_factor=1.2, **kwargs) -> None:
        """Addin tables to the plot area"""
        if df is None or df.empty:
            return
        
        if self.current_ax:
            for table in list(self.current_ax.tables):
                table.remove()
        
        clean_kwargs = {k: v for k, v in kwargs.items() if k not in ["xlabel", "ylabel", "title", "legend"]}

        table_object = pd.plotting.table(
            self.current_ax,
            df,
            loc=loc,
            **clean_kwargs
        )

        table_object.auto_set_font_size(auto_font_size)
        if not auto_font_size:
            table_object.set_fontsize(fontsize)
        table_object.scale(scale_factor, scale_factor)
    
    def _apply_common_formatting(self, kwargs: Dict[str, Any]) -> None:
        """Apply common formatting to plots\n
        This method is now deprecated as formatting is done in individual plot methods"""
        pass
    
    def clear_plot(self) -> None:
        """Clear the current plot"""
        if self.current_figure:
            self.setup_layout(1, 1)
    
    def get_figure(self) -> Figure:
        """Return the current figure"""
        return self.current_figure

    def _helper_format_categorical_axis(self, axis, labels):
        """Format categorical axis with better tick spacing"""
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
        
        if axis == self.current_ax.xaxis:
            plt.setp(self.current_ax.get_xticklabels(), rotation=45, ha="right")

    def _helper_is_datetime_column(self, plot_tab: "PlotTab", data) -> bool:
        """Check if data is datetime"""
        if data is None:
            return False
        
        try:
            if isinstance(data, pd.Series):
                if pd.api.types.is_datetime64_any_dtype(data):
                    return True
                if data.dtype == "object":
                    if data.empty:
                        return False
                    sample_val = None
                    for val in data.head(50):
                        if val is not None:
                            sample_val = val
                            break
                    if sample_val is None:
                        return False
                    
                    if not isinstance(sample_val, str):
                        return False
                    try:
                        pd.to_datetime(sample_val, utc=True)
                        return True
                    except:
                        pass
            elif hasattr(data, "dtype"):
                return pd.api.types.is_datetime64_any_dtype(data.dtype)
        except Exception as DateTimeColumnError:
            plot_tab.status_bar.log(f"Datetime detection warning: {str(DateTimeColumnError)}", LogLevel.WARNING)
        return False

    def _helper_apply_auto_datetime_format(self, plot_tab: "PlotTab", axis, data):
        """Apply datetime formatting based on the input datarange"""
        if data is None or len(data) < 2 or not self._helper_is_datetime_column(plot_tab, data):
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
        except Exception as ApplyDateTimeError:
            plot_tab.status_bar.log(f"Failed to auto-format datetime: {str(ApplyDateTimeError)}", LogLevel.WARNING)

    def _helper_set_intelligent_locator(self, plot_tab: "PlotTab", axis, data):
        """Set tick locators based on tghe datarange"""
        if data is None or len(data) < 2 or not self._helper_is_datetime_column(plot_tab, data):
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
        except Exception as DateTimeLocatorError:
            plot_tab.status_bar.log(f"Failed to set datetime locator: {str(DateTimeLocatorError)}", LogLevel.WARNING)
    
    def _helper_format_datetime_axis(self, plot_tab: "PlotTab", ax, x_data, y_data=None) -> None:
        """Format datetime axes with tick spacing"""

        #first check if datetime in cols
        is_x_datetime = self._helper_is_datetime_column(plot_tab, x_data)
        is_y_datetime = self._helper_is_datetime_column(plot_tab, y_data) if y_data is not None else False

        use_custom_format: bool = plot_tab.custom_datetime_check.isChecked()

        #format the x-axis
        if is_x_datetime:
            try:
                if isinstance(x_data, pd.Series):
                    if x_data.dtype == "object":
                        x_data = pd.to_datetime(x_data, utc=True, errors="coerce")
                    elif not hasattr(x_data.dtype, "tz") or x_data.dtype.tz is None:
                        x_data = x_data.dt.tz_localize("UTC", nonexistent="shift_forward", ambiguous="infer")
            except Exception as FormatDateTimeAxisError:
                plot_tab.status_bar.log(f"X-axis timezone handling: {str(FormatDateTimeAxisError)}", LogLevel.WARNING)
            
            if use_custom_format:
                format_text = plot_tab.x_datetime_format_combo.currentText()

                if format_text == "Custom":
                    custom_format = plot_tab.x_custom_datetime_input.text().strip()
                    if custom_format:
                        try:
                            ax.xaxis.set_major_formatter(mdates.DateFormatter(custom_format))
                            self._helper_set_intelligent_locator(plot_tab, ax.xaxis, x_data)
                        except Exception as FormatDateTimeAxisError:
                            plot_tab.status_bar.log(f"Invalid datetime format: {str(FormatDateTimeAxisError)}", LogLevel.WARNING)
                            self._helper_apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
                    else:
                        self._helper_apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
                elif format_text == "Auto":
                    self._helper_apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
                else:
                    format_code = format_text.split(" ")[0]
                    try:
                        ax.xaxis.set_major_formatter(mdates.DateFormatter(format_code))
                        self._helper_set_intelligent_locator(plot_tab, ax.xaxis, x_data)
                    except Exception as FormatDateTimeAxisError:
                        plot_tab.status_bar.log(f"Invalid datetime format: {str(FormatDateTimeAxisError)}", LogLevel.WARNING)
                        self._helper_apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)
            else:
                self._helper_apply_auto_datetime_format(plot_tab, ax.xaxis, x_data)

        #fmt yaxis
        if is_y_datetime:
            try:
                if isinstance(y_data, pd.Series):
                    if y_data.dtype == 'object':
                        y_data = pd.to_datetime(y_data, utc=True, errors='coerce')
                    elif not hasattr(y_data.dtype, 'tz') or y_data.dtype.tz is None:
                        y_data = y_data.dt.tz_localize('UTC', nonexistent='shift_forward', ambiguous='infer')
            except Exception as FormatYAxisDateTimeError:
                plot_tab.status_bar.log(f"Y-axis timezone handling: {str(FormatYAxisDateTimeError)}", LogLevel.WARNING)
            
            if use_custom_format:
                format_text = plot_tab.y_datetime_format_combo.currentText()

                if format_text == "Custom":
                    custom_format = plot_tab.y_custom_datetime_format_input.text().strip()
                    if custom_format:
                        try:
                            ax.yaxis.set_major_formatter(mdates.DateFormatter(custom_format))
                            self._helper_set_intelligent_locator(plot_tab, ax.yaxis, y_data)
                        except Exception as FormatYAxisDateTimeError:
                            plot_tab.status_bar.log(f"Invalid datetime format: {str(FormatYAxisDateTimeError)}", LogLevel.WARNING)
                            self._helper_apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
                    else:
                        self._helper_apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
                elif x_data is not None and hasattr(x_data, "dtype") and (x_data.dtype == "object" or isinstance(x_data.dtype, pd.CategoricalDtype)):
                    try:
                        labels = x_data.unique()
                        labels = [l for l in labels if pd.notna(l)]
                        self._helper_format_categorical_axis(ax.xaxis, labels)
                    except Exception:
                        pass
                elif format_text == "Auto":
                    self._helper_apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
                else:
                    format_code = format_text.split(" ")[0]
                    try:
                        ax.yaxis.set_major_formatter(mdates.DateFormatter(format_code))
                        self._helper_set_intelligent_locator(plot_tab, ax.yaxis, y_data)
                    except Exception as InvalidDateTimeError:
                        plot_tab.status_bar.log(f"Invalid datetime format: {str(InvalidDateTimeError)}", "WARNING")
                        self._helper_apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
            else:
                self._helper_apply_auto_datetime_format(plot_tab, ax.yaxis, y_data)
    
    def _helper_apply_flipped_labels(self, plot_tab: "PlotTab", x_col, y_cols, font_family):
        """Function to correctly apply axes labels when flipped axes is true"""
        if plot_tab.xlabel_check.isChecked():
            ylabel_to_use = plot_tab.xlabel_input.text() or x_col
            self.current_ax.set_ylabel(
                ylabel_to_use,
                fontsize=plot_tab.xlabel_size_spin.value(),
                fontweight=plot_tab.xlabel_weight_combo.currentText(),
                fontfamily=font_family
            )
        
        if plot_tab.ylabel_check.isChecked():
            xlabel_to_use = plot_tab.ylabel_input.text() or (y_cols[0] if len(y_cols) == 1 else str(y_cols))
            self.current_ax.set_xlabel(
                xlabel_to_use,
                fontsize=plot_tab.ylabel_size_spin.value(),
                fontweight=plot_tab.ylabel_weight_combo.currentText(),
                fontfamily=font_family
            )
        
        if plot_tab.title_check.isChecked():
            title_to_use = plot_tab.title_input.text() if plot_tab.title_input.text() else plot_tab.plot_type.currentIndex()
            self.current_ax.set_title(
                title_to_use,
                fontsize=plot_tab.title_size_spin.value(),
                fontweight=plot_tab.title_weight_combo.currentText(),
                fontfamily=font_family
            )
    
    def _helper_add_regression_analysis(self, plot_tab: "PlotTab", x_col: str, y_col: str, flipped: bool = False) -> None:
        """Orchestrates regression calculation via RegressionAnalyzer and renders output."""
        try:
            from core.regression_analyser import RegressionAnalyser, RegressionType, ErrorBarType
            reg_type_str = plot_tab.view.regression_type_combo.currentText() if hasattr(plot_tab, "regression_type_combo") else "Linear"
            try:
                reg_type = RegressionType(reg_type_str)
            except ValueError:
                reg_type = RegressionType.LINEAR
            
            try:
                x_data, y_data = RegressionAnalyser.clean_data(plot_tab.data_handler.df, x_col, y_col, reg_type)
            except TypeError as Type_err:
                plot_tab.status_bar.log(f"Regression skipped: {str(Type_err)}", "INFO")
                return
            
            if len(x_data) < 2:
                plot_tab.status_bar.log("Not enough data points to perform regression analysis", "WARNING")
                return
            degree = plot_tab.view.poly_degree_spin.value() if hasattr(plot_tab, "poly_degree_spin") else 2
            try:
                result = RegressionAnalyser.compute_fit(x_data, y_data, reg_type, degree)
            except RuntimeError:
                plot_tab.status_bar.log(f"{reg_type.value} fit failed to converge", "ERROR")
                return
            
            if plot_tab.view.regression_line_check.isChecked():
                self._render_regression_line(result.x_line, result.y_line, reg_type, flipped)
            
            if plot_tab.view.confidence_interval_check.isChecked():
                confidence = plot_tab.view.confidence_level_spin.value() / 100.0
                margin = RegressionAnalyser.compute_confidence_interval(x_data, result.residuals, result.x_line, confidence)
                self._render_confidence_interval(result.x_line, result.y_line, margin, confidence, flipped)
            
            self._render_regression_statistics(plot_tab, result.metrics, flipped)
            
            plot_tab.status_bar.log(
            f"Regression ({reg_type.value}): R²={result.metrics.r_squared:.4f}, RMSE={result.metrics.rmse:.4f}",
            "SUCCESS"
            )
        except Exception as error:
            plot_tab.status_bar.log(f"Regression analysis failed: {str(error)}", "ERROR")
            import traceback
            print(f"Regression error: {traceback.format_exc()}")
    
    def _render_regression_line(self, x_line: np.ndarray, y_line: np.ndarray, reg_type: Any, flipped: bool) -> None:
        plot_args = (x_line, y_line) if not flipped else (y_line, x_line)
        reg_line = self.current_ax.plot(
            *plot_args, color="red", linestyle="-", linewidth=2,
            label=f"{reg_type.value} Fit", alpha=0.5
        )[0]
        reg_line.set_gid("regression_line")
    
    def _render_confidence_interval(self, x_line: np.ndarray, y_line: np.ndarray, margin: np.ndarray, confidence: float, flipped: bool) -> None:
        fill_args = (x_line, y_line - margin, y_line + margin) if not flipped else (y_line - margin, y_line + margin, x_line)
        if not flipped:
            ci_poly = self.current_ax.fill_between(
                fill_args[0], fill_args[1], fill_args[2],
                color="red", alpha=0.15, label=f"{int(confidence*100)}% CI", zorder=-1
            )
        else:
            ci_poly = self.current_ax.fill_betweenx(
                fill_args[2], fill_args[0], fill_args[1],
                color="red", alpha=0.15, label=f"{int(confidence*100)}% CI", zorder=-1
            )
        ci_poly.set_gid("confidence_interval")
    
    def _render_regression_statistics(self, plot_tab: 'PlotTab', metrics: RegressionMetrics, flipped: bool) -> None:
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
            self.current_ax.text(
                0.05, 0.95, textstr, transform=self.current_ax.transAxes, 
                fontsize=11, verticalalignment='top', bbox=props, 
                fontfamily=font_family, zorder=15
            )
    
    def add_error_bars(self, df: pd.DataFrame, x_col: str, y_cols: List[str], error_bar_type_str: str, flipped: bool = False, plot_tab: "PlotTab" = None) -> None:
        """Computes standard deviation and standard error bars"""
        from core.regression_analyser import ErrorBarType
        import numpy as np
        
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
            
            data_line, caplines, barcols = self.current_ax.errorbar(
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
    
    def _ensure_projection(self, is_3d: bool) -> None:
        """Replaces the current axis with 3D or 2D"""
        if not self.current_ax or not self.current_figure:
            return
        
        current_is_3d = hasattr(self.current_ax, "zaxis")
        if current_is_3d == is_3d:
            return
        
        geometry = self.current_ax.get_subplotspec()
        try:
            idx = self.axes_flat.index(self.current_ax)
        except ValueError:
            idx = -1
        
        self.current_figure.delaxes(self.current_ax)
        
        if is_3d:
            self.current_ax = self.current_figure.add_subplot(geometry, projection="3d")
        else:
            self.current_ax = self.current_figure.add_subplot(geometry)
        
        if idx >= 0:
            self.axes_flat[idx] = self.current_ax
    
    def _apply_camera_view(self, elevation=None, azimuth=None) -> None:
        """Applies 3d camera angles"""
        if elevation is not None or azimuth is not None:
            self.current_ax.view_init(elev=elevation, azim=azimuth)
    
    def plot_scatter_3d(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a 3d scatter plot"""
        self._clear_axes()
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        zlabel = kwargs.pop("zlabel", None)
        legend = kwargs.pop("legend", True)
        hue = kwargs.pop("hue", None)
        cmap_name = kwargs.pop("cmap", None)
        
        kwargs.pop("secondary_y", None)
        kwargs.pop("secondary_plot_type", None)
        elevation = kwargs.pop("elevation", None)
        azimuth = kwargs.pop("azimuth", None)
        
        self._apply_camera_view(elevation, azimuth)
        
        mask = df[x].notna() & df[y].notna() & df[z].notna()
        
        if hue and hue in df.columns:
            groups = df[hue].dropna().unique()
            colors = self._get_colors_from_cmap(cmap_name, len(groups))
            
            for i, group in enumerate(groups):
                group_mask = mask & (df[hue] == group)
                c = colors[i] if colors else None
                self.current_ax.scatter3D(
                    df.loc[group_mask, x].to_numpy(),
                    df.loc[group_mask, y].to_numpy(),
                    df.loc[group_mask, z].to_numpy(),
                    label=str(group), color=c, picker=5, **kwargs
                )
        else:
            if cmap_name: kwargs["cmap"] = cmap_name
            self.current_ax.scatter3D(df.loc[mask, x].to_numpy(), df.loc[mask, y].to_numpy(), df.loc[mask, z].to_numpy(), picker=5, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, legend, zlabel=zlabel, **kwargs)
    
    def plot_line_3d(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a 3D line plot."""
        self._clear_axes()
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        zlabel = kwargs.pop('zlabel', None)
        legend = kwargs.pop('legend', True)
        hue = kwargs.pop('hue', None)
        cmap_name = kwargs.pop("cmap", None)
        
        kwargs.pop("secondary_y", None)
        kwargs.pop("secondary_plot_type", None)
        elevation = kwargs.pop("elevation", None)
        azimuth = kwargs.pop("azimuth", None)

        self._apply_camera_view(elevation, azimuth)

        mask = df[x].notna() & df[y].notna() & df[z].notna()

        if hue and hue in df.columns:
            groups = df[hue].dropna().unique()
            colors = self._get_colors_from_cmap(cmap_name, len(groups))
            
            for i, group in enumerate(groups):
                group_mask = mask & (df[hue] == group)
                c = colors[i] if colors else None
                self.current_ax.plot3D(
                    df.loc[group_mask, x].to_numpy(), 
                    df.loc[group_mask, y].to_numpy(), 
                    df.loc[group_mask, z].to_numpy(), 
                    label=str(group), color=c, picker=5, **kwargs
                )
        else:
            colors = self._get_colors_from_cmap(cmap_name, 1)
            c = colors[0] if colors else None
            if c: kwargs["color"] = c
            self.current_ax.plot3D(df.loc[mask, x].to_numpy(), df.loc[mask, y].to_numpy(), df.loc[mask, z].to_numpy(), label=f"{y} vs {z}", picker=5, **kwargs)
        
        self._set_labels(title, xlabel, ylabel, legend, zlabel=zlabel, **kwargs)

    def plot_surface_3d(self, df: pd.DataFrame, x: str, y: str, z: str, **kwargs) -> None:
        """Create a 3D surface plot from gridded data."""
        self._clear_axes()
        title = kwargs.pop('title', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        zlabel = kwargs.pop('zlabel', None)
        _ = kwargs.pop("legend", None)
        cmap_name = kwargs.pop("cmap", "viridis")

        kwargs.pop("secondary_y", None)
        kwargs.pop("secondary_plot_type", None)
        elevation = kwargs.pop("elevation", None)
        azimuth = kwargs.pop("azimuth", None)

        self._apply_camera_view(elevation, azimuth)

        X, Y, Z = self._prepare_gridded_data(df, x, y, z)
        X_grid, Y_grid = np.meshgrid(X, Y)

        surf = self.current_ax.plot_surface(X_grid, Y_grid, Z, cmap=cmap_name, **kwargs)
        self.current_figure.colorbar(surf, ax=self.current_ax, label=zlabel if zlabel else z)

        self._set_labels(title, xlabel, ylabel, False, zlabel=zlabel, **kwargs)
    
    # Plot strategies
    def execute_strategy(self, plot_type: str, plot_tab: "PlotTab", x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> Optional[str]:
        from core.plot_strategies.strat_registry import StrategyRegistry
        try:
            is_3d_plot = plot_type in ["3D Scatter", "3D Line", "3D Surface"]
            self._ensure_projection(is_3d_plot)
            
            strategy = StrategyRegistry.get_strategy(plot_type)
            return strategy.execute(
                engine=self,
                plot_tab=plot_tab,
                x_col=x_col,
                y_cols=y_cols,
                axes_flipped=axes_flipped,
                font_family=font_family,
                plot_kwargs=plot_kwargs,
                general_kwargs=general_kwargs
            )
        except ValueError as error:
            return str(error)
        except Exception as error:
            return f"Failed to execute plotting sequence for {plot_type}. Error: {str(error)}"
        
    def _validate_geospatial_data(self, gdf: Any) -> bool:
        """Validates if the provided data is a valid GeoDataFrame and GeoPandas is installed"""
        if gpd is None:
            self.current_ax.text(0.5, 0.5, "GeoPandas is required for this plot.\nPlease install it first", ha="center", va="center", fontsize=12, color="red")
            return False
        if not isinstance(gdf, gpd.GeoDataFrame):
            self.current_ax.text(0.5, 0.5, "Data is not a GeoDataFrame.\nEnsure a 'geometry' column is present", ha="center", va="center", fontsize=12, color="red")
            return False
        
        return True
    
    def _handle_geospatial_crs(self, gdf: "gpd.GeoDataFrame", target_crs: Optional[str], add_basemap: bool) -> "gpd.GeoDataFrame":
        if gdf.crs is None:
            print("Warning. Data has no CRS defined")
            try:
                gdf.set_crs("EPSG:4326")
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
    
    def _configure_geospatial_legend(self, gdf: "gpd.GeoDataFrame", column: Optional[str], legend: bool, orientation: Optional[str], legend_kwds: Dict[str, Any], use_divider: bool, kwargs: Dict[str, Any]) -> Tuple[bool, bool, Dict[str, Any]]:
        """Configures the legend properties based on given data type and the orientation given"""
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

    def _setup_geospatial_cax(self, use_divider: bool, column: Optional[str], legend: bool, orientation: Optional[str]) -> Any:
        """Sets up a colorbar axis if the axis divider is requested"""
        cax = None
        if use_divider and column and legend:
            try:
                divider = make_axes_locatable(self.current_ax)
                if orientation == "horizontal":
                    cax = divider.append_axes("bottom", size="5%", pad=0.1)
                else:
                    cax = divider.append_axes("right", size="5%", pad=0.1)
                
                self.current_ax._cax = cax
            except Exception as DividerError:
                print(f"Error creating axis divider: {DividerError}")
        
        return cax
    
    def _add_geospatial_basemap(
        self,
        gdf: "gpd.GeoDataFrame",
        add_basemap: bool,
        basemap_source: str,
        basemap_zoom: Any
    ) -> None:
        """Applies a basemap to the current ploy using Contextiliy"""
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
                        self.current_ax,
                        crs=gdf.crs.to_string(),
                        source=provider,
                        zoom=basemap_zoom
                    )
                else:
                    print("Unable to add basemap: CRS is undefined")
            except Exception as BaseMapError:
                print(f"Failed to add basemap: {BaseMapError}")
        elif add_basemap and not ctx:
            self.current_ax.text(0.02, 0.02, "Instal contextily for basemap support", transform=self.current_ax.transAxes, fontsize=8, color="red", bbox=dict(facecolor="white", alpha=0.7))
    
    def plot_geospatial(self, gdf: "gpd.GeoDataFrame", column: Optional[str] = None, **kwargs) -> None:
        """Create a geospatial plot"""
        if not self._validate_geospatial_data(gdf):
            return
        
        target_crs = kwargs.pop("target_crs", None)
        add_basemap = kwargs.pop("add_basemap", False)
        basemap_source = kwargs.pop("basemap_source", "OpenStreetMap")
        basemap_zoom = kwargs.pop("basemap_zoom", "auto")
        
        gdf = self._handle_geospatial_crs(gdf, target_crs, add_basemap)
        title = kwargs.pop("title", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        legend = kwargs.pop("legend", True)
        orientation = kwargs.pop("orientation", None)
        legend_kwds = kwargs.pop("legend_kwds", {})
        use_divider = kwargs.pop("use_divider", False)
        cax_enabled = kwargs.pop("cax_enabled", False)
        axis_off = kwargs.pop("axis_off", False)
        
        legend, is_categorical, legend_kwds = self._configure_geospatial_legend(gdf, column, legend, orientation, legend_kwds, use_divider, kwargs)
        cax = self._setup_geospatial_cax(use_divider, column, legend, orientation)
        
        if "cmap" not in kwargs and not is_categorical:
            kwargs["cmap"] = "viridis"
        
        if column and column in gdf:
            gdf.plot(column=column, ax=self.current_ax, cax=cax, legend=legend, legend_kwds=legend_kwds, **kwargs)
        else:
            kwargs.pop("cmap", None)
            gdf.plot(ax=self.current_ax, **kwargs)
        
        if axis_off:
            self.current_ax.set_axis_off()
        
        self._add_geospatial_basemap(gdf, add_basemap, basemap_source, basemap_zoom)
        self._set_labels(title, xlabel, ylabel, False, **kwargs)