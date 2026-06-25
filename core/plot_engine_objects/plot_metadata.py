from typing import Dict

AVAILABLE_PLOTS: Dict[str, str] = {
    'Line'               : 'plot_line',
    'Scatter'            : 'plot_scatter',
    'Bar'                : 'plot_bar',
    'Histogram'          : 'plot_histogram',
    'Box'                : 'plot_box',
    'Violin'             : 'plot_violin',
    'Heatmap'            : 'plot_heatmap',
    'KDE'                : 'plot_kde',
    'Area'               : 'plot_area',
    'Pie'                : 'plot_pie',
    'Count Plot'         : 'plot_count',
    'Hexbin'             : 'plot_hexbin',
    '2D Density'         : 'plot_density_2d',
    "Stem"               : "plot_stem",
    "Stackplot"          : "plot_stackplot",
    "Stairs"             : "plot_stairs",
    "Eventplot"          : "plot_eventplot",
    "ECDF"               : "plot_ecdf",
    "2D Histogram"       : "plot_hist2d",
    "Image Show (imshow)": "plot_imshow",
    "pcolormesh"         : "plot_pcolormesh",
    "Contour"            : "plot_contour",
    "Contourf"           : "plot_contourf",
    "Barbs"              : "plot_barbs",
    "Quiver"             : "plot_quiver",
    "Streamplot"         : "plot_streamplot",
    "Tricontour"         : "plot_tricontour",
    "Tricontourf"        : "plot_tricontourf",
    "Tripcolor"          : "plot_tripcolor",
    "Triplot"            : "plot_triplot",
    "GeoSpatial"         : "plot_geospatial",
    "3D Scatter"         : "plot_scatter_3d",
    "3D Line"            : "plot_line_3d",
    "3D Surface"         : "plot_surface_3d",
}

PLOT_DESCRIPTIONS: Dict[str, str] = {
    "Line"               : "A line chart is a type of graph that displays information as a series of data points connected by straight line segments. It is commonly used to visualize trends and changes in data over continuous intervals, such as time. The horizontal axis (x-axis) typically represents a sequential progression (e.g., time), and the vertical axis (y-axis) shows a quantitative value.",

    "Scatter"            : "A scatter plot is a graph that uses dots to represent the values of two different numeric variables, showing the relationship between them. Each dot's position on the horizontal (x-axis) and vertical (y-axis) indicates the values for an individual data point. Scatter plots are used to observe patterns, trends, and correlations between variables, such as determining if an increase in one variable corresponds with an increase or decrease in another. ",

    "Bar"                : "A bar chart is a data visualization tool that uses rectangular bars to represent categorical data, with the length or height of the bars proportional to the values they represent. It is used to compare different categories and show variations in data, making it useful for visualizing things like sales figures, survey responses, or monthly rainfall. Bar charts can be oriented vertically or horizontally and can display one or more sets of data.",

    "Histogram"          : "A histogram is a graphical representation of the distribution of a set of numerical data. It uses bars to show the frequency of data points that fall into specific, consecutive ranges or 'bins'. The height of each bar indicates the number of data points in that bin, making it useful for visualizing the shape, center, and spread of the data.",

    "Box"                : "A box plot is a graphical tool that visualizes the distribution of numerical data through its quartiles, providing a five-number summary: minimum, first quartile ((Q_{1})), median, third quartile ((Q_{3})), and maximum. It uses a box to represent the middle 50%  of the data (the interquartile range, or (IQR)), with a line inside for the median. 'Whiskers' extend from the box to the minimum and maximum values, and outliers may be shown as individual points beyond the whiskers.",

    "Violin"             : "A violin plot is a statistical visualization that combines a box plot with a kernel density plot to show the distribution of a numeric variable for one or more groups. The plot's shape is determined by the data density—it is wider where values are more frequent and narrower where they are less frequent, providing a visual representation of peaks in the data. Inside the violin shape, a miniature box plot can be included to display summary statistics like the median and interquartile range.",

    "Heatmap"            : "A heatmap is a data visualization technique that uses color to represent the magnitude of a variable, making complex data easier to interpret. It typically displays data as a grid of colored squares, where the intensity or shade of the color corresponds to the data's value, ranging from 'cool' (low values) to 'hot' (high values). Common uses include showing user behavior on websites, such as clicks and scroll depth, as well as representing geographical or statistical data like population density or temperature variations.",

    "KDE"                : "A kernel density estimation (KDE) plot is a visualization that creates a smooth curve to show the distribution of a continuous variable, acting as a smoothed-out version of a histogram. It is a non-parametric way to estimate the probability density function (PDF) of the data, helping to identify patterns, trends, and outliers in a clearer, more continuous way than with a histogram.",

    "Area"               : "An area chart is a type of line chart that shows quantitative data over time by filling the space between the plotted line and the axis with color or shading. It is used to emphasize the volume or magnitude of change over time, and can also be used to show how different data series contribute to a total.",

    "Pie"                : "A pie chart is a circular graphic that represents parts of a whole, with each 'slice' of the pie showing the proportional size of a category. The slices are proportional to the quantities they represent, and all slices combined make up the whole, typically equaling 100%.",

    "Count Plot"         : "A count plot can be thought of as a histogram across a categorical, instead of quantitative, variable. The basic API and options are identical to those for barplot(), so you can compare counts across nested variables.",

    "Hexbin"             : "A hexbin plot is a type of 2D histogram that represents the density of data points in a scatter plot by dividing the graphing area into hexagonal bins. Instead of showing individual points, it uses a color gradient to show how many data points fall into each hexagon, making it useful for visualizing large datasets where points would otherwise overlap.",

    "2D Density"         : "A 2D density plot visualizes the relationship between two numeric variables by showing the concentration of data points in a 2D space. It uses a color gradient to represent areas with a high density of points, making it useful for identifying patterns in large datasets where a scatterplot would result in overplotting. Common types include 2D histograms with squares or hexagons and contour plots.",
    "Stem"               : "A stem plot draws vertical lines at each x-position to a y-value, with a marker at the top. It is excellent for visualizing discrete time series or categorical data points.",
    "Stackplot"          : "A stackplot (or stacked area chart) visualizes the contribution of different groups to a whole over time or another continuous variable. Each colored area represents one group, and the areas are stacked on top of each other.",
    "Stairs"             : "A stairs plot creates a step-like visualization, similar to a line plot but with vertical and horizontal lines only (no diagonals). It's useful for displaying data that changes at discrete intervals.",
    "Eventplot"          : "An eventplot visualizes identical-looking objects (e.g., lines) at different positions. It's commonly used for plotting spike trains or other event-based data, where the position on one axis represents the time or location of an event.",
    "ECDF"               : "An Empirical Cumulative Distribution Function (ECDF) plot shows the proportion of data points that are less than or equal to a given value. It's a step function that provides a clear visual of the data's distribution.",
    "2D Histogram"       : "A 2D histogram (hist2d) bins the data into 2D rectangles and uses color to represent the number of data points in each bin. It is excellent for visualizing the joint distribution of two variables with a large number of points.",
    "Image Show (imshow)": "Displays data as an image, where the data is represented by colors. This is used for visualizing 2D arrays or matrices, such as a correlation matrix. Requires data to be in a 2D grid format (use X, Y-pos, and Z-value).",
    "pcolormesh"         : "Creates a pseudocolor plot of a 2D array. It's highly efficient for plotting large arrays and is often used for 2D histograms or other gridded data. Requires data to be in a 2D grid format (use X, Y-pos, and Z-value).",
    "Contour"            : "A contour plot displays 3D data in 2D by showing lines (contours) that connect points of equal value (like a topographical map). It requires data to be in a 2D grid (use X, Y-pos, and Z-value).",
    "Contourf"           : "A filled contour plot (contourf) is similar to a contour plot but fills the areas between the contour lines with colors. Requires data to be in a 2D grid (use X, Y-pos, and Z-value).",
    "Barbs"              : "A barb plot is used to visualize vector fields, typically in meteorology to show wind direction and speed. Requires X, Y-position and U, V vector components (4 columns).",
    "Quiver"             : "A quiver plot displays a 2D field of arrows. Each arrow represents a vector at a specific (x, y) point. Requires X, Y-position and U, V vector components (4 columns).",
    "Streamplot"         : "A streamplot visualizes a 2D vector field by drawing streamlines. It's excellent for understanding the flow of a vector field. Requires gridded X, Y-position and U, V vector components (4 columns).",
    "Tricontour"         : "A triangular contour plot. Similar to a regular contour plot, but it works on an unstructured grid of (x, y, z) data points by first creating a triangulation.",
    "Tricontourf"        : "A filled triangular contour plot. Like `contourf`, it fills the areas between the contour lines generated from an unstructured (x, y, z) dataset.",
    "Tripcolor"          : "Creates a pseudocolor plot from an unstructured (x, y, z) dataset. It triangulates the (x, y) points and colors each triangle based on its Z value.",
    "Triplot"            : "A simple plot that draws the underlying triangulation of an (x, y) dataset, showing the network of triangles used for other tri-plots.",
    "GeoSpatial"         : "Visualizes geospatial data using GeoPandas. Requires a GeoDataFrame (imported from .shp, .geojson, etc.). The 'X Column' can be used to select a column for choropleth coloring (values determine color).",
    "3D Scatter"         : "A 3D scatter plot visualizes data points in a three-dimensional space. Requires X, Y, and Z columns mapped to respective dimensions.",
    "3D Line"            : "A 3D line plot connects data points in a three-dimensional sequence. Requires X, Y, and Z columns.",
    "3D Surface"         : "A 3D surface plot visualizes gridded data as a continuous surface. Requires X, Y, and Z columns mapped to a 2D grid."
}