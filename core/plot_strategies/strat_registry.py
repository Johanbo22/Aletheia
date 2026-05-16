from typing import Dict, Type
from core.plot_strategies.base_strategy import BasePlotStrategy
from core.plot_strategies.count_strategy import CountPlotStrategy
from core.plot_strategies.density2d_strategy import Density2DPlotStrategy
from core.plot_strategies.ecdf_strategy import ECDFPlotStrategy
from core.plot_strategies.eventplot_strategy import EventplotPlotStrategy
from core.plot_strategies.geospatial_strategy import GeoSpatialPlotStrategy
from core.plot_strategies.heatmap_strategy import HeatmapPlotStrategy
from core.plot_strategies.hexbin_strategy import HexbinPlotStrategy
from core.plot_strategies.histogram2d_strategy import Histogram2DPlotStrategy
from core.plot_strategies.histogram_strategy import HistogramPlotStrategy
from core.plot_strategies.gridded_strategies import ContourFPlotStrategy, ContourPlotStrategy, ImshowPlotStrategy, PColormeshPlotStrategy
from core.plot_strategies.kde_strategy import KDEPlotStrategy
from core.plot_strategies.line_strategy import LinePlotStrategy
from core.plot_strategies.area_strategy import AreaPlotStrategy
from core.plot_strategies.pie_strategy import PiePlotStrategy
from core.plot_strategies.scatter_strategy import ScatterPlotStrategy
from core.plot_strategies.bar_strategy import BarPlotStrategy
from core.plot_strategies.box_strategy import BoxPlotStrategy
from core.plot_strategies.stackplot_strategy import StackPlotStrategy
from core.plot_strategies.stair_strategy import StairsPlotStrategy
from core.plot_strategies.stem_strategy import StemPlotStrategy
from core.plot_strategies.trig_strategies import TricontourPlotStrategy, TricontourfPlotStrategy, TripcolorPlotStrategy, TriplotPlotStrategy
from core.plot_strategies.vector_strategies import BarbsPlotStrategy, QuiverPlotStrategy, StreamplotPlotStrategy
from core.plot_strategies.violin_strategy import ViolinPlotStrategy
from core.plot_strategies.three_d_strategies import Line3DStrategy, Scatter3DStrategy, Surface3DStrategy


class StrategyRegistry:
    _strategies: Dict[str, Type[BasePlotStrategy]] = {
        "Line": LinePlotStrategy,
        "Area": AreaPlotStrategy,
        "Scatter": ScatterPlotStrategy,
        "Bar": BarPlotStrategy,
        "Box": BoxPlotStrategy,
        "Histogram": HistogramPlotStrategy,
        "Violin": ViolinPlotStrategy,
        "Pie": PiePlotStrategy,
        "Heatmap": HeatmapPlotStrategy,
        "KDE": KDEPlotStrategy,
        "Count Plot": CountPlotStrategy,
        "Hexbin": HexbinPlotStrategy,
        "2D Density": Density2DPlotStrategy,
        "Stem": StemPlotStrategy,
        "Stackplot": StackPlotStrategy,
        "Stairs": StairsPlotStrategy,
        "Eventplot": EventplotPlotStrategy,
        "2D Histogram": Histogram2DPlotStrategy,
        "ECDF": ECDFPlotStrategy,
        "Image Show (imshow)": ImshowPlotStrategy,
        "PColormesh": PColormeshPlotStrategy,
        "Contour": ContourPlotStrategy,
        "Contourf": ContourFPlotStrategy,
        "Barbs": BarbsPlotStrategy,
        "Quiver": QuiverPlotStrategy,
        "Streamplot": StreamplotPlotStrategy,
        "Tricontour": TricontourPlotStrategy,
        "Tricontourf": TricontourfPlotStrategy,
        "Tripcolor": TripcolorPlotStrategy,
        "Triplot": TriplotPlotStrategy,
        "GeoSpatial": GeoSpatialPlotStrategy,
        "3D Line": Line3DStrategy,
        "3D Scatter": Scatter3DStrategy,
        "3D Surface": Surface3DStrategy,
    }
    
    @classmethod
    def get_strategy(cls, plot_type: str) -> BasePlotStrategy:
        strategy_class = cls._strategies.get(plot_type)
        if not strategy_class:
            raise ValueError(f"No plotting strategy registered for {plot_type}")
        return strategy_class()