from typing import TYPE_CHECKING, List, Dict, Any, Optional
from core.plot_engine import PlotEngine
from core.plot_strategies.base_strategy import BasePlotStrategy
from ui.plot_tab import PlotTab

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine
    from ui.plot_tab import PlotTab

class HistogramPlotStrategy(BasePlotStrategy):
    def execute(self, engine: PlotEngine, plot_tab: PlotTab, x_col: str, y_cols: List[str], axes_flipped: bool, font_family: str, plot_kwargs: Dict[str, Any], general_kwargs: Dict[str, Any]) -> str | None:
        df = plot_tab.data_handler.df
        engine._clear_axes()

        if len(y_cols) > 1:
            plot_tab.status_bar.log(f"Histogram only supports one column. Using: {y_cols[0]}", "WARNING")

        # Use first y_col as the data source, or x_col if y_cols is empty
        data_col = y_cols[0] if y_cols else x_col

        title = general_kwargs.pop('title', None)

        # Try to get xlabel from input, fallback to data_col
        xlabel_input = ""
        if hasattr(plot_tab, "xlabel_input"):
            xlabel_input = plot_tab.xlabel_input.text()
        elif hasattr(plot_tab, "view") and hasattr(plot_tab.view, "xlabel_input"):
            xlabel_input = plot_tab.view.xlabel_input.text()

        xlabel = general_kwargs.pop('xlabel', xlabel_input or data_col)
        ylabel = general_kwargs.pop('ylabel', None)
        legend = general_kwargs.pop('legend', True)
        cmap_name = general_kwargs.pop("cmap", None)
        hue = general_kwargs.pop("hue", None)

        bins = plot_kwargs.pop('bins', general_kwargs.pop('bins', 30))
        show_normal = plot_kwargs.pop("show_normal", general_kwargs.pop("show_normal", False))
        show_kde = plot_kwargs.pop("show_kde", general_kwargs.pop("show_kde", False))
        show_stats = plot_kwargs.pop("show_stats", general_kwargs.pop("show_stats", True))

        if hasattr(plot_tab, "histogram_bins_spin"):
            bins = plot_tab.histogram_bins_spin.value()
        if hasattr(plot_tab, "histogram_show_normal_check"):
            show_normal = plot_tab.histogram_show_normal_check.isChecked()
        if hasattr(plot_tab, "histogram_show_kde_check"):
            show_kde = plot_tab.histogram_show_kde_check.isChecked()

        kwargs = plot_kwargs.copy()
        if axes_flipped:
            kwargs["orientation"] = "horizontal"

        if hue and hue in df.columns:
            groups = df[hue].dropna().unique()
            data_list = []
            labels = []
            for group in groups:
                group_data = df[df[hue] == group][data_col].dropna()
                if not group_data.empty:
                    data_list.append(group_data)
                    labels.append(str(group))

            plot_data = data_list
            colors = engine._get_colors_from_cmap(cmap_name, len(data_list))
            if colors:
                kwargs["color"] = colors
            kwargs["label"] = labels
        else:
            plot_data = df[data_col].dropna()
            colors = None

        n, bins_edges, patches = engine.current_ax.hist(
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
                        if axes_flipped:
                            engine.current_ax.plot(normal_curve, x, color=c, linestyle="-", linewidth=2,
                                                   label=f"Norm ({labels[i]})")
                        else:
                            engine.current_ax.plot(x, normal_curve, color=c, linestyle="-", linewidth=2,
                                                   label=f"Norm ({labels[i]})")
                if show_kde:
                    from scipy.stats import gaussian_kde
                    try:
                        kde = gaussian_kde(group_data)
                        x = np.linspace(group_data.min(), group_data.max(), 100)
                        kde_curve = kde(x)
                        if axes_flipped:
                            engine.current_ax.plot(kde_curve, x, color=c, linestyle="--", linewidth=2,
                                                   label=f"KDE ({labels[i]})")
                        else:
                            engine.current_ax.plot(x, kde_curve, color=c, linestyle="--", linewidth=2,
                                                   label=f"KDE ({labels[i]})")
                    except Exception:
                        pass
            if legend or show_normal or show_kde:
                engine.current_ax.legend()
        else:
            data = plot_data
            mu = data.mean()
            sigma = data.std()
            median = data.median()

            if show_normal and sigma > 0:
                from scipy.stats import norm
                x = np.linspace(data.min(), data.max(), 100)
                normal_curve = norm.pdf(x, mu, sigma)
                if axes_flipped:
                    engine.current_ax.plot(normal_curve, x, "r-", linewidth=2.5,
                                           label=f"Normal (µ={mu:.2f}, σ={sigma:.2f})")
                else:
                    engine.current_ax.plot(x, normal_curve, "r-", linewidth=2.5,
                                           label=f"Normal (µ={mu:.2f}, σ={sigma:.2f})")

            if show_kde:
                from scipy.stats import gaussian_kde
                try:
                    kde = gaussian_kde(data)
                    x = np.linspace(data.min(), data.max(), 100)
                    kde_curve = kde(x)
                    if axes_flipped:
                        engine.current_ax.plot(kde_curve, x, "g-", linewidth=2.5, label="KDE")
                    else:
                        engine.current_ax.plot(x, kde_curve, "g-", linewidth=2.5, label="KDE")
                except Exception:
                    pass

            if show_normal or show_kde:
                engine.current_ax.legend()

            if show_stats and (show_normal or show_kde):
                stats_text = f"µ = {mu:.3f}\nσ = {sigma:.3f}\nmedian = {median:.3f}\nn = {len(data)}"
                props = dict(boxstyle="round", facecolor="wheat", alpha=0.85, edgecolor="black", linewidth=1)
                engine.current_ax.text(0.75, 0.95, stats_text, transform=engine.current_ax.transAxes, fontsize=10,
                                       verticalalignment="top", bbox=props, fontfamily="monospace")

        if axes_flipped:
            engine._set_labels(title, ylabel, xlabel, False, **general_kwargs)
            try:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, None, df[data_col])
            except Exception:
                pass
        else:
            engine._set_labels(title, xlabel, ylabel, False, **general_kwargs)
            try:
                engine._helper_format_datetime_axis(plot_tab, engine.current_ax, df[data_col])
            except Exception:
                pass

        return None