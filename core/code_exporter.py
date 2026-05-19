# core/code_exporter.py
from typing import Dict, Any, List, Set, Callable
from datetime import datetime
from pathlib import Path
import pandas as pd

from resources.version import APPLICATION_NAME

class CodeExporter:
    """
    Generates a complete, runnable Python script by inspecting
    the final UI state of the DataHandler and PlotTab.
    """
    
    def __init__(self) -> None:
        self.imports: Set[str] = set()
        self.script_lines: List[str] = []

    def _add_imports(self, plot_config: Dict[str, Any]) -> None:
        """Dynamically add required imports based on UI config."""
        self.imports.clear()
        self.imports.update([
            "import pandas as pd",
            "import numpy as np",
            "import matplotlib.pyplot as plt",
            "import seaborn as sns",
            "import requests",
            "from io import StringIO",
            "import traceback",
            "from sqlalchemy import create_engine",
            "from sqlalchemy.sql import text"
        ])
        
        plot_type = plot_config.get("plot_type")
        axes_cfg = plot_config.get("axes", {})
        
        if axes_cfg.get("datetime", {}).get("enabled"):
            self.imports.add("import matplotlib.dates as mdates")
        
        if axes_cfg.get("x_axis", {}).get("max_ticks", 10) < 30 or \
           axes_cfg.get("y_axis", {}).get("max_ticks", 10) < 30:
            self.imports.add("from matplotlib.ticker import MaxNLocator")
        
        scatter_analysis = plot_config.get("advanced", {}).get("scatter", {})
        if any([
            scatter_analysis.get("show_regression"),
            scatter_analysis.get("show_ci"),
            scatter_analysis.get("show_r2"),
            scatter_analysis.get("show_rmse"),
            scatter_analysis.get("show_equation"),
            scatter_analysis.get("error_bars", "None") != "None"
        ]):
            self.imports.add("from scipy import stats")
            if scatter_analysis.get("show_ci"):
                self.imports.add("from scipy.stats import t as t_dist")

        hist_analysis = plot_config.get("advanced", {}).get("histogram", {})
        if hist_analysis.get("show_normal"):
            self.imports.add("from scipy.stats import norm")
        if hist_analysis.get("show_kde") or plot_type == "KDE":
            self.imports.add("from scipy.stats import gaussian_kde")

    def _clean_value(self, value: Any) -> str:
        """Helper to format values for insertion into code safely."""
        if hasattr(value, "tolist") and hasattr(value, "dtype"):
            return self._clean_value(value.tolist())
        if isinstance(value, str):
            return repr(value)
        if value is None:
            return "None "
        if isinstance(value, dict):
            items = [f"{self._clean_value(k)}: {self._clean_value(v)}" for k, v in value.items()]
            return "{ " + ",  ".join(items) + "} "
        if isinstance(value, (list, tuple, set)):
            cleaned_items = []
            for v in value:
                if hasattr(v, 'tolist') and hasattr(v, 'dtype'):
                    cleaned_items.extend([self._clean_value(x) for x in v.tolist()])
                else:
                    cleaned_items.append(self._clean_value(v))
            cleaned_items = [f"'{str(item).strip('\'"')}'" for item in cleaned_items]
            return "[" + ",  ".join(cleaned_items) + "]"
        return str(value)

    def _generate_header(self) -> str:
        """Generates the script header and imports."""
        header = [
            "\"\"\"",
            f"{APPLICATION_NAME} - Generated Analysis Script",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This script replicates the data loading, processing, and",
            f"visualization steps performed in {APPLICATION_NAME}.",
            "\"\"\"",
            "",
        ]
        header.extend(sorted(list(self.imports)))
        return "\n".join(header)

    def _generate_data_loader(self, data_filepath: str, source_info: Dict[str, Any]) -> str:
        """Generates the data loading section."""
        lines = ["", "def load_data():", "    \"\"\"Load data from source.\"\"\""]
        
        if source_info.get("last_db_connection_string") and source_info.get("last_db_query"):
            conn_string = self._clean_value(source_info.get("last_db_connection_string"))
            query = self._clean_value(source_info.get("last_db_query"))
            
            lines.extend([
                "    print('Loading data from Database...')",
                f"    connection_string = {conn_string}",
                f"    query = text({query})",
                "    try:",
                "        engine = create_engine(connection_string)",
                "        with engine.connect() as connection:",
                "            df = pd.read_sql_query(query, connection)",
                "        print('Data loaded successfully from database.')",
                "        return df",
                "    except ImportError:",
                "        print('Error: Missing database driver. Please install, e.g., pip install psycopg2-binary')",
                "        return None",
                "    except Exception as e:",
                "        print(f'Failed to load from database: {e}')",
                "        print('Please check connection string, query, and drivers.')",
                "        return None"
            ])

        elif source_info.get("is_temp_file"):
            sheet_id = self._clean_value(source_info.get("last_gsheet_id"))
            sheet_name = self._clean_value(source_info.get("last_gsheet_name"))
            delimiter = self._clean_value(source_info.get("last_gsheet_delimiter", ","))
            decimal = self._clean_value(source_info.get("last_gsheet_decimal", "."))
            thousands = self._clean_value(source_info.get("last_gsheet_thousands"))

            lines.extend([
                "    print('Loading data from Google Sheets...')",
                f"    sheet_id = {sheet_id}",
                f"    sheet_name = {sheet_name}",
                "    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}'",
                "    try:",
                "        response = requests.get(url, timeout=10)",
                "        response.raise_for_status()",
                f"        df = pd.read_csv(StringIO(response.text), sep={delimiter}, decimal={decimal}, thousands={thousands}, engine='python', on_bad_lines='skip')",
                "        print('Data loaded successfully.')",
                "        return df",
                "    except Exception as e:",
                "        print(f'Failed to load Google Sheet: {e}')",
                "        return None"
            ])
            
        else:
            filepath_str = self._clean_value(data_filepath)
            ext = Path(data_filepath).suffix.lower()
            lines.extend([
                f"    filepath = {filepath_str}",
                "    print(f'Loading data from {filepath}...')",
                "    try:"
            ])
            
            if ext in ['.xlsx', '.xls']:
                lines.append("        df = pd.read_excel(filepath)")
            elif ext == '.json':
                lines.append("        df = pd.read_json(filepath)")
            elif ext == '.txt':
                lines.append("        df = pd.read_csv(filepath, sep='\\t')")
            else:
                lines.append("        df = pd.read_csv(filepath)")
                
            lines.extend([
                "        print('Data loaded successfully.')",
                "        return df",
                "    except Exception as e:",
                "        print(f'Failed to load local file: {e}')",
                "        return None"
            ])
            
        lines.append("\n")
        return "\n".join(lines)

    def _generate_data_ops(self, data_operations: List[Dict[str, Any]]) -> str:
        """Generates the data processing function."""
        lines = ["", "def process_data(df):", "    \"\"\"Apply data operations.\"\"\""]
        if not data_operations:
            lines.extend([
                "    print('No data operations to apply.')",
                "    return df"
            ])
            return "\n".join(lines)
            
        lines.extend([
            "    print('Applying data operations...')",
            "    df_processed = df.copy()"
        ])
        
        for i, op in enumerate(data_operations):
            op_type = op.get("type")
            lines.append(f"\n    # Operation {i+1}: {op_type}")
            
            try:
                if op_type == "filter":
                    col = self._clean_value(op['column'])
                    cond = op['condition']
                    val = op['value'] 
                    
                    allowed_ops = {"==", "!=", ">", "<", ">=", "<=", "contains", "in"}
                    if cond not in allowed_ops:
                        lines.append(f"    # Warning: Skipping unsafe/unknown filter condition '{cond}'")
                        continue
                    
                    val_str = self._clean_value(val)
                    lines.extend([
                        "    try:",
                        "        # Attempt numeric conversion for filter value",
                        f"        filter_val = {val_str}",
                        "        if isinstance(filter_val, (int, float)):",
                        f"            df_processed[{col}] = pd.to_numeric(df_processed[{col}], errors='coerce')",
                        "    except Exception:",
                        f"        filter_val = {val_str}"
                    ])

                    if cond == "contains":
                        lines.append(f"    df_processed = df_processed[df_processed[{col}].astype(str).str.contains(str(filter_val), na=False, regex=False)]")
                    elif cond == "in":
                        val_list = [val] if not isinstance(val, (list, tuple, set)) else val
                        lines.append(f"    df_processed = df_processed[df_processed[{col}].isin({self._clean_value(val_list)})]")
                    else:
                        lines.append(f"    df_processed = df_processed[df_processed[{col}] {cond} filter_val]")
                
                elif op_type == "drop_duplicates":
                    lines.append("    df_processed = df_processed.drop_duplicates()")
                
                elif op_type == "drop_missing":
                    lines.append("    df_processed = df_processed.dropna()")
                
                elif op_type == "fill_missing":
                    method_raw = op.get('method', 'ffill')
                    if method_raw in ['ffill', 'bfill']:
                        lines.append(f"    df_processed = df_processed.{method_raw}()")
                    else:
                        method_str = self._clean_value(method_raw)
                        lines.append(f"    df_processed = df_processed.fillna(value={method_str})")
                
                elif op_type == "drop_column":
                    col = self._clean_value(op['column'])
                    lines.append(f"    df_processed = df_processed.drop(columns=[{col}])")
                
                elif op_type == "rename_column":
                    old = self._clean_value(op['old_name'])
                    new = self._clean_value(op['new_name'])
                    lines.append(f"    df_processed = df_processed.rename(columns={{{old}: {new}}})")
                
                elif op_type == "change_data_type":
                    col = self._clean_value(op['column'])
                    new_type = op['new_type']
                    if new_type == "string":
                        lines.append(f"    df_processed[{col}] = df_processed[{col}].astype(pd.StringDtype())")
                    elif new_type == "int":
                        lines.append(f"    df_processed[{col}] = pd.to_numeric(df_processed[{col}], errors='coerce').astype(pd.Int64Dtype())")
                    elif new_type == "float":
                        lines.append(f"    df_processed[{col}] = pd.to_numeric(df_processed[{col}], errors='coerce').astype(pd.Float64Dtype())")
                    elif new_type == "category":
                        lines.append(f"    df_processed[{col}] = df_processed[{col}].astype('category')")
                    elif new_type == "datetime":
                        lines.append(f"    df_processed[{col}] = pd.to_datetime(df_processed[{col}], errors='coerce', utc=True)")
                
                elif op_type == "aggregate":
                    group_by = op['group_by']
                    agg_cols = op['agg_columns']
                    agg_func = op['agg_func']
                    agg_dict = ", ".join([f"{self._clean_value(c)}: {self._clean_value(agg_func)}" for c in agg_cols])
                    lines.append(f"    df_processed = df_processed.groupby({self._clean_value(group_by)}).agg({{{agg_dict}}}).reset_index()")
            
            except Exception as e:
                lines.append(f"    # FAILED TO PARSE OPERATION: {op} -> {e}")
        
        lines.append("\n    print('Data operations applied.')")
        lines.append("    return df_processed")
        return "\n".join(lines)

    def _generate_scatter_analysis(self, get_cfg: Callable[[str, Any], Any], x_col: str, y_col_str: str, flip_axes: bool) -> List[str]:
        """Helper to generate scatter plot analysis code."""
        lines = []
        scatter_cfg = get_cfg("advanced.scatter", {})
        
        # Guard against generating regression logic if there's no valid Y-axis selected
        if y_col_str in ["'None'", '"None"', "None"]:
            return lines

        if not any([
            scatter_cfg.get("show_regression"), scatter_cfg.get("show_ci"), 
            scatter_cfg.get("show_r2"), scatter_cfg.get("show_rmse"), 
            scatter_cfg.get("show_equation"), scatter_cfg.get("error_bars", "None") != "None"
        ]):
            return lines

        lines.extend([
            "\n    # --- Scatter Plot Analysis ---",
            "    try:",
            "        # Prepare data for analysis (drop NaNs)",
            f"        analysis_df = df[[{x_col}, {y_col_str}]].dropna().copy()",
            f"        x_data_raw = analysis_df[{x_col}].values",
            f"        y_data_raw = analysis_df[{y_col_str}].values",
            "        if len(x_data_raw) < 2:",
            "            print('Not enough data for regression analysis.')",
            "        else:",
            "            slope, intercept, r_value, p_value, std_err = stats.linregress(x_data_raw, y_data_raw)",
            "            x_line = np.linspace(x_data_raw.min(), x_data_raw.max(), 100)",
            "            y_line = slope * x_line + intercept"
        ])
        
        if scatter_cfg.get("show_regression"):
            lines.append("            # Plot regression line")
            lines.append(f"            ax.plot({ 'y_line, x_line' if flip_axes else 'x_line, y_line'}, color='red', ls='-', lw=2, label='Linear Fit', gid='regression_line')")
        
        if scatter_cfg.get("show_ci"):
            lines.extend([
                "            # Calculate and plot confidence interval",
                f"            confidence = {scatter_cfg.get('ci_level', 95) / 100.0}",
                "            n = len(x_data_raw)",
                "            residuals = y_data_raw - (slope * x_data_raw + intercept)",
                "            residual_std = np.sqrt(np.sum(residuals**2) / (n - 2))",
                "            x_mean = np.mean(x_data_raw)",
                "            se_line = residual_std * np.sqrt(1/n + (x_line - x_mean)**2 / np.sum((x_data_raw - x_mean)**2))",
                "            t_val = t_dist.ppf((1 + confidence) / 2, n - 2)",
                "            margin = t_val * se_line"
            ])
            if flip_axes:
                lines.append("            ax.fill_betweenx(x_line, y_line - margin, y_line + margin, color='red', alpha=0.15, label=f'{int(confidence*100)}% CI', gid='confidence_interval')")
            else:
                lines.append("            ax.fill_between(x_line, y_line - margin, y_line + margin, color='red', alpha=0.15, label=f'{int(confidence*100)}% CI', gid='confidence_interval')")

        lines.extend([
            "            # Prepare stats text",
            "            stats_text = []",
            f"            eq_x, eq_y = ('y', 'x') if {flip_axes} else ('x', 'y')"
        ])
        
        if scatter_cfg.get("show_equation"):
            lines.extend([
                "            op = '+' if intercept >= 0 else '-'",
                "            stats_text.append(f'{eq_y} = {slope:.4f}{eq_x} {op} {abs(intercept):.4f}')"
            ])
        if scatter_cfg.get("show_r2"):
            lines.append("            stats_text.append(f'R² = {r_value**2:.4f}')")
        if scatter_cfg.get("show_rmse"):
            lines.extend([
                "            y_pred = slope * x_data_raw + intercept",
                "            rmse = np.sqrt(np.mean((y_data_raw - y_pred)**2))",
                "            stats_text.append(f'RMSE = {rmse:.4f}')"
            ])
        
        lines.extend([
            "            if stats_text:",
            "                textstr = '\\n'.join(stats_text)",
            "                props = dict(boxstyle='round', facecolor='wheat', alpha=0.85)",
            f"                ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=11, verticalalignment='top', bbox=props, fontfamily={self._clean_value(get_cfg('appearance.font_family', 'Arial'))})"
        ])

        error_bar_type = scatter_cfg.get("error_bars", "None")
        if error_bar_type == "Standard Deviation":
            lines.append("            # (Standard Deviation error bar export is complex, skipping for now)") 
        elif error_bar_type == "Standard Error":
            lines.extend([
                "            # Add Standard Error bars",
                "            y_pred_all = slope * x_data_raw + intercept",
                "            residuals = y_data_raw - y_pred_all",
                "            residual_std = np.sqrt(np.sum(residuals**2) / (len(x_data_raw) - 2))",
                "            x_mean = np.mean(x_data_raw)",
                "            se_points = residual_std * np.sqrt(1/len(x_data_raw) + (x_data_raw - x_mean)**2 / np.sum((x_data_raw - x_mean)**2))",
                "            step = max(1, len(x_data_raw) // 30)",
                "            err_args = (x_data_raw[::step], y_data_raw[::step])",
                f"            err_kwargs = {{'yerr': se_points[::step]}} if not {flip_axes} else {{'xerr': se_points[::step]}}",
                "            ax.errorbar(*err_args, **err_kwargs, fmt='o', ecolor='gray', markersize=3, alpha=0.5, capsize=4, zorder=8, markerfacecolor='none', markeredgecolor='none', elinewidth=1, linestyle='none')"
            ])

        lines.extend([
            "    except Exception as e:",
            "        print(f'Failed to add scatter analysis: {e}')",
            "        traceback.print_exc()"
        ])
        
        return lines

    def _get_cfg(self, config: Dict[str, Any], path: str, default: Any = None) -> Any:
        """Get the information nested in config using dot notation"""
        keys = path.split(".")
        val = config
        try:
            for key in keys:
                val = val[key]
            return val
        except (KeyError, TypeError, AttributeError):
            return default
    
    def _generate_figure_setup(self, config: Dict[str, Any]) -> List[str]:
        """Generate the code for the figure initialization and global styling params"""
        lines = ["\n    # --- 1. Set up Figure and Style ---"]
        
        style = self._clean_value(self._get_cfg(config, "appearance.figure.style", "default"))
        lines.extend([
            "    try:",
            f"        plt.style.use({style})",
            "    except Exception as style_error:",
            "        print(f'Warning: Failed to use style {style}: {style_error}')",
            "        plt.style.use('default')"
        ])

        font_family = self._clean_value(self._get_cfg(config, 'appearance.font_family', 'Arial'))
        lines.append(f"    plt.rcParams['font.family'] = {font_family}")

        width = self._get_cfg(config, 'appearance.figure.width', 10)
        height = self._get_cfg(config, 'appearance.figure.height', 6)
        dpi = self._get_cfg(config, 'appearance.figure.dpi', 100)
        
        plot_type = self._get_cfg(config, "plot_type")
        is_3d_plot = plot_type in ["3D Scatter", "3D Line", "3D Surface"]
        subplot_kwargs = "projection='3d'" if is_3d_plot else ""
        
        if subplot_kwargs:
            lines.append(f"    fig, ax = plt.subplots(figsize=({width}, {height}), dpi={dpi}, subplot_kw={{{self._clean_value('projection')}: {self._clean_value('3d')}}})")
        else:
            lines.append(f"    fig, ax = plt.subplots(figsize=({width}, {height}), dpi={dpi})")
        
        bg_color = self._clean_value(self._get_cfg(config, 'appearance.figure.bg_color', 'white'))
        face_color = self._clean_value(self._get_cfg(config, 'appearance.figure.face_color', 'white'))
        
        if bg_color != "'white'": 
            lines.append(f"    fig.set_facecolor({bg_color})")
        if face_color != "'white'": 
            lines.append(f"    ax.set_facecolor({face_color})")
        
        return lines
    
    def _generate_data_prep(self, df: pd.DataFrame, config: Dict[str, Any], x_col: str, y_cols: List[str]) -> List[str]:
        """Generate the code used to preprare datetime data"""
        lines = ["\n    # --- 2. Data Preparation ---"]
        
        cols_to_convert = []
        
        if x_col and x_col in df.columns:
            if "datetime" in str(df.dtypes.get(x_col, '')):
                cols_to_convert.append(x_col)
        
        for y_c in y_cols:
            if y_c in df.columns and "datetime" in str(df.dtypes.get(y_c, '')):
                cols_to_convert.append(y_c)
        
        if cols_to_convert:
            lines.extend([
                "    # Convert detected datetime columns",
                "    try:"
            ])
            for col in set(cols_to_convert):
                lines.append(f"        df[{self._clean_value(col)}] = pd.to_datetime(df[{self._clean_value(col)}], errors='coerce', utc=True)")
            lines.append("    except Exception as e: print(f'Warning: Date conversion failed: {e}')")
        
        if self._get_cfg(config, "basic.use_subset"):
            subset_name = self._clean_value(self._get_cfg(config, "basic.subset_name"))
            lines.append(f"    print(f'Note: processing full dataset, but UI was viewing subset: {{ {subset_name} }}')")

        return lines
    
    def _generate_plot_dispatch(self, config: Dict[str, Any], x_col: str, y_cols: List[str], hue: str, palette: str) -> List[str]:
        """Method to call the specific plot generation based on plot type"""
        lines = ["\n    # --- 3. Generate Plot ---"]
        plot_type = self._get_cfg(config, "plot_type", "Scatter")
        lines.append(f"    # Plot Type: {plot_type}")

        alpha = self._get_cfg(config, "advanced.global_alpha", 1.0)
        flip = self._get_cfg(config, "axes.flip_axes", False)
        
        ctx = {
            "x": x_col, 
            "y": self._clean_value(y_cols[0]) if y_cols else None,
            "ys": self._clean_value(y_cols),
            "y_list": y_cols,
            "z": self._clean_value(self._get_cfg(config, "basic.z_column")),
            "hue": self._clean_value(hue) if hue and hue != "None" else "None",
            "palette": self._clean_value(palette),
            "alpha": alpha,
            "flip": flip,
            "config": config
        }
        
        if plot_type == "Line": lines.extend(self._generate_line_plot(ctx))
        elif plot_type == "Scatter": lines.extend(self._generate_scatter_plot(ctx))
        elif plot_type == "Bar": lines.extend(self._generate_bar_plot(ctx))
        elif plot_type == "Histogram": lines.extend(self._generate_histogram(ctx))
        elif plot_type == "Box": lines.extend(self._generate_box_plot(ctx))
        elif plot_type == "Violin": lines.extend(self._generate_violin_plot(ctx))
        elif plot_type == "Area": lines.extend(self._generate_area_plot(ctx))
        elif plot_type == "Pie": lines.extend(self._generate_pie_chart(ctx))
        elif plot_type == "Heatmap": lines.extend(self._generate_heatmap(ctx))
        elif plot_type == "KDE": lines.extend(self._generate_kde_plot(ctx))
        elif plot_type in ["Hexbin", "2D Density", "2D Histogram"]: lines.extend(self._generate_2d_distribution(ctx, plot_type))
        elif plot_type in ["Stem", "Stairs", "Eventplot", "ECDF", "Stackplot"]: lines.extend(self._generate_specialty_plot(ctx, plot_type))
        elif plot_type in ["Image Show (imshow)", "pcolormesh", "Contour", "Contourf"]: lines.extend(self._generate_gridded_plot(ctx, plot_type))
        elif plot_type in ["Barbs", "Quiver", "Streamplot"]: lines.extend(self._generate_vector_plot(ctx, plot_type))
        elif plot_type in ["Tricontour", "Tricontourf", "Tripcolor", "Triplot"]: lines.extend(self._generate_tri_plot(ctx, plot_type))
        elif plot_type == "GeoSpatial": lines.extend(self._generate_geospatial_plot(ctx))
        elif plot_type == "3D Scatter": lines.extend(self._generate_3d_scatter(ctx))
        elif plot_type == "3D Line": lines.extend(self._generate_3d_line(ctx))
        elif plot_type == "3D Surface": lines.extend(self._generate_3d_surface(ctx))
        else:
            lines.append(f"    sns.scatterplot(data=df, x={ctx['x']}, y={ctx['y']}, alpha={alpha})")
        
        return lines
    
    def _generate_line_plot(self, ctx: Dict) -> List[str]:
        lines = []
        g_line = self._get_cfg(ctx["config"], "advanced.global_line", {})
        g_marker = self._get_cfg(ctx["config"], "advanced.global_marker", {})

        marker = self._clean_value(g_marker.get("shape", "None"))
        marker = f"{marker} if {marker} != 'None' else None"

        kwargs = [
            f"marker={marker}",
            f"markersize={g_marker.get('size', 6)}",
            f"linestyle={self._clean_value(g_line.get('style', '-'))}",
            f"linewidth={g_line.get('width', 1.5)}",
            f"alpha={ctx['alpha']}"
        ]
        kwargs_str = ", ".join(kwargs)
        if ctx['hue'] != "None":
            lines.extend([
                f"    groups = df[{ctx['hue']}].unique()",
                "    for group in groups:",
                f"        mask = df[{ctx['hue']}] == group",
                f"        for col in {ctx['ys']}:",
                "            # Plot with Hue"
            ])
            plot_cmd = f"ax.plot(df.loc[mask, {ctx['x']}], df.loc[mask, col], label=f'{{col}} - {{group}}', {kwargs_str})"
            if ctx['flip']:
                plot_cmd = f"ax.plot(df.loc[mask, col], df.loc[mask, {ctx['x']}], label=f'{{col}} - {{group}}', {kwargs_str})"
            lines.append(f"            {plot_cmd}")
        else:
            lines.append(f"    for col in {ctx['ys']}:")
            plot_cmd = f"ax.plot(df[{ctx['x']}], df[col], label=col, {kwargs_str})"
            if ctx['flip']:
                plot_cmd = f"ax.plot(df[col], df[{ctx['x']}], label=col, {kwargs_str})"
            lines.append(f"        {plot_cmd}")
        return lines
    
    def _generate_scatter_plot(self, ctx: Dict) -> List[str]:
        lines = []
        g_marker = self._get_cfg(ctx['config'], "advanced.global_marker", {})
        size = g_marker.get('size', 6)
        
        kw_base = [f"s={size}**2", f"alpha={ctx['alpha']}"]
        
        marker = self._clean_value(g_marker.get('shape', 'o'))
        if marker != "'None'": kw_base.append(f"marker={marker}")
        
        edge = self._clean_value(g_marker.get('edge_color'))
        if edge != "'Auto'": kw_base.append(f"edgecolors={edge}")
        
        c = self._clean_value(g_marker.get('color'))
        if c != "'Auto'": kw_base.append(f"c={c}")

        if ctx['hue'] != "None":
            x_var, y_var = (ctx['x'], ctx['y']) if not ctx['flip'] else (ctx['y'], ctx['x'])
            kw = [
                f"data=df, x={x_var}, y={y_var}",
                f"hue={ctx['hue']}, palette={ctx['palette']}",
                f"s={size}**2, alpha={ctx['alpha']}, ax=ax"
            ]
            if marker != "'None'": kw.append(f"marker={marker}")
            
            lines.append(f"    sns.scatterplot({', '.join(kw)})")
        else:
            lines.append(f"    for col in {ctx['ys']}:")
            
            x_var, y_var = (f"df[{ctx['x']}]", "df[col]") if not ctx['flip'] else ("df[col]", f"df[{ctx['x']}]")
            
            kw = kw_base.copy()
            kw.insert(0, f"x={x_var}, y={y_var}")
            kw.append("label=col")
            
            lines.append(f"        ax.scatter({', '.join(kw)})")

        return lines
    
    def _generate_bar_plot(self, ctx: Dict) -> List[str]:
        lines = []
        g_bar = self._get_cfg(ctx['config'], "advanced.global_bar", {})
        width = g_bar.get('width', 0.8)
        
        if ctx['hue'] != "None" and len(ctx['y_list']) == 1:
            orient = "'h'" if ctx['flip'] else "'v'"
            x_var, y_var = (ctx['x'], ctx['y']) if not ctx['flip'] else (ctx['y'], ctx['x'])
            
            lines.extend([
                f"    sns.barplot(data=df, x={x_var}, y={y_var}, hue={ctx['hue']},",
                f"                orient={orient}, palette={ctx['palette']}, alpha={ctx['alpha']}, ax=ax)"
            ])
        else:
            lines.extend([
                f"    x_labels = df[{ctx['x']}].unique()",
                "    x_pos = np.arange(len(x_labels))",
                f"    bar_width = {width} / {len(ctx['y_list'])}",
                f"    for i, col in enumerate({ctx['ys']}):",
                f"        offset = (i - {len(ctx['y_list'])}/2) * bar_width + bar_width/2",
                f"        vals = [df[df[{ctx['x']}]==l][col].values[0] if not df[df[{ctx['x']}]==l].empty else 0 for l in x_labels]"
            ])
            
            if ctx['flip']:
                lines.extend([
                    f"        ax.barh(x_pos + offset, vals, height=bar_width, label=col, alpha={ctx['alpha']})",
                    "    ax.set_yticks(x_pos)",
                    "    ax.set_yticklabels(x_labels)"
                ])
            else:
                lines.extend([
                    f"        ax.bar(x_pos + offset, vals, width=bar_width, label=col, alpha={ctx['alpha']})",
                    "    ax.set_xticks(x_pos)",
                    "    ax.set_xticklabels(x_labels)"
                ])
        return lines
    
    def _generate_histogram(self, ctx: Dict) -> List[str]:
        lines = []
        hist_cfg = self._get_cfg(ctx['config'], "advanced.histogram", {})
        bins = hist_cfg.get('bins', 30)
        density = "True" if hist_cfg.get('show_normal') or hist_cfg.get('show_kde') else "False"
        
        lines.extend([
            f"    data = df[{ctx['y']}].dropna()",
            f"    _, bins, _ = ax.hist(data, bins={bins}, density={density}, alpha={ctx['alpha']}, label='Histogram')"
        ])
        
        if hist_cfg.get('show_normal'):
            lines.extend([
                "    # Overlay Normal Distribution",
                "    mu, sigma = data.mean(), data.std()",
                "    y_norm = norm.pdf(np.linspace(bins[0], bins[-1], 100), mu, sigma)",
                "    ax.plot(np.linspace(bins[0], bins[-1], 100), y_norm, 'r-', lw=2, label='Normal Dist')"
            ])
            
        if hist_cfg.get('show_kde'):
            lines.extend([
                "    # Overlay KDE",
                "    kde = gaussian_kde(data)",
                "    x_kde = np.linspace(bins[0], bins[-1], 100)",
                "    ax.plot(x_kde, kde(x_kde), 'g--', lw=2, label='KDE')"
            ])
            
        return lines
    
    def _generate_box_plot(self, ctx: Dict) -> List[str]:
        vert = str(not ctx['flip'])
        return [f"    df.boxplot(column={ctx['ys']}, ax=ax, vert={vert})"]

    def _generate_violin_plot(self, ctx: Dict) -> List[str]:
        x_var, y_var = (ctx['x'], ctx['y']) if not ctx['flip'] else (ctx['y'], ctx['x'])
        orient = "'h'" if ctx['flip'] else "'v'"
        return [f"    sns.violinplot(data=df, x={x_var}, y={y_var}, hue={ctx['hue']}, orient={orient}, palette={ctx['palette']}, ax=ax)"]

    def _generate_area_plot(self, ctx: Dict) -> List[str]:
        lines = [
            "    try:",
            f"        df_plot = df.set_index({ctx['x']})[{ctx['ys']}]",
            f"        if {ctx['flip']}:",
            "            # Area plot doesn't support direct flip in pandas, using fill_betweenx manually",
            f"            for col in {ctx['ys']}:",
            f"                ax.fill_betweenx(df_plot.index, 0, df_plot[col], label=col, alpha={ctx['alpha']})",
            "        else:",
            f"            df_plot.plot(kind='area', stacked=True, alpha={ctx['alpha']}, colormap={ctx['palette']}, ax=ax)",
            "    except Exception as e: print(f'Area plot error: {e}')"
        ]
        return lines

    def _generate_pie_chart(self, ctx: Dict) -> List[str]:
        lines = []
        pie_cfg = self._get_cfg(ctx['config'], "advanced.pie", {})
        lines.extend([
            "    try:",
            f"        data = df.groupby({ctx['x']})[{ctx['y']}].sum()"
        ])
        
        explode_list = "None"
        if pie_cfg.get("explode_first"):
             dist = pie_cfg.get("explode_distance", 0.1)
             lines.append("        explode = [0.0] * len(data)")
             lines.append(f"        if len(explode) > 0: explode[0] = {dist}")
             explode_list = "explode"
             
        autopct = "'%1.2f%%'" if pie_cfg.get("show_percentages") else "None"
        start = pie_cfg.get("start_angle", 0)
        shadow = pie_cfg.get("shadow", False)
        
        is_donut = pie_cfg.get("donut_enabled", False)
        
        if is_donut:
            donut_width = pie_cfg.get("donut_width", 0.3)
            wedgeprops_str = f"{{'width': {donut_width}}}"
            lines.append(f"        ax.pie(data, labels=data.index, autopct={autopct}, startangle={start}, explode={explode_list}, shadow={shadow}, wedgeprops={wedgeprops_str})")
        else:
            lines.append(f"        ax.pie(data, labels=data.index, autopct={autopct}, startangle={start}, explode={explode_list}, shadow={shadow})")
        
        lines.extend([
            "        ax.set_ylabel('')",
            "    except Exception as e: print(f'Pie chart error: {e}')"
        ])
        return lines
    
    def _generate_heatmap(self, ctx: Dict) -> List[str]:
        return [
            "    # Heatmap of correlations",
            "    numeric = df.select_dtypes(include=[np.number])",
            f"    sns.heatmap(numeric.corr(), annot=True, cmap={ctx['palette']}, ax=ax)"
        ]

    def _generate_kde_plot(self, ctx: Dict) -> List[str]:
        return [f"    df[{ctx['y']}].plot(kind='kde', ax=ax, alpha={ctx['alpha']})"]

    def _generate_2d_distribution(self, ctx: Dict, plot_type: str) -> List[str]:
        lines = []
        if plot_type == "Hexbin":
            x_v, y_v = (ctx['x'], ctx['y']) if not ctx['flip'] else (ctx['y'], ctx['x'])
            lines.append(f"    ax.hexbin(df[{x_v}], df[{y_v}], gridsize=20, cmap={ctx['palette']})")
        elif plot_type == "2D Density":
            lines.append(f"    sns.kdeplot(data=df, x={ctx['x']}, y={ctx['y']}, fill=True, cmap={ctx['palette']}, ax=ax)")
        elif plot_type == "2D Histogram":
             lines.extend([
                 f"    h = ax.hist2d(df[{ctx['x']}], df[{ctx['y']}], cmap={ctx['palette']})",
                 "    fig.colorbar(h[3], ax=ax)"
             ])
        return lines
    
    def _generate_specialty_plot(self, ctx: Dict, plot_type: str) -> List[str]:
        lines = []
        if plot_type == "Stem":
            lines.append(f"    ax.stem(df[{ctx['x']}], df[{ctx['y']}])")
        elif plot_type == "Stairs":
            lines.append(f"    ax.stairs(df[{ctx['y']}], edges=np.arange(len(df)+1)) # Approximation")
        elif plot_type == "Eventplot":
             lines.extend([
                 "    # Eventplot expects list of lists",
                 f"    data = [df[c].dropna().values for c in {ctx['ys']}]",
                 f"    ax.eventplot(data, alpha={ctx['alpha']})"
             ])
        elif plot_type == "ECDF":
             lines.append(f"    ax.ecdf(df[{ctx['y']}])")
        elif plot_type == "Stackplot":
             lines.extend([
                 "    # Ensure sorted X",
                 f"    dfs = df.sort_values(by={ctx['x']})",
                 f"    ax.stackplot(dfs[{ctx['x']}], dfs[{ctx['ys']}].T, labels={ctx['ys']}, alpha={ctx['alpha']})",
                 "    ax.legend(loc='upper left')"
             ])
        return lines
    
    def _generate_gridded_plot(self, ctx: Dict, plot_type: str) -> List[str]:
        lines = []
        z = self._clean_value(ctx['y_list'][1] if len(ctx['y_list']) > 1 else None)
        if z == "None" or z == "'None'": return ["    print('Error: Z-axis column missing for gridded plot')"]
        
        lines.extend([
            "    # Prepare Gridded Data",
            f"    piv = df.pivot_table(index={ctx['y']}, columns={ctx['x']}, values={z}, aggfunc='mean')",
            "    X, Y = np.meshgrid(piv.columns, piv.index)",
            "    Z = piv.values"
        ])
        
        if plot_type == "Image Show (imshow)":
            lines.extend([
                f"    im = ax.imshow(Z, origin='lower', aspect='auto', cmap={ctx['palette']})",
                "    fig.colorbar(im, ax=ax)"
            ])
        elif plot_type == "Contour":
            lines.append(f"    ax.contour(X, Y, Z, cmap={ctx['palette']})")
        elif plot_type == "Contourf":
            lines.extend([
                f"    cf = ax.contourf(X, Y, Z, cmap={ctx['palette']})",
                "    fig.colorbar(cf, ax=ax)"
            ])
        elif plot_type == "pcolormesh":
            lines.extend([
                f"    pcm = ax.pcolormesh(X, Y, Z, cmap={ctx['palette']})",
                "    fig.colorbar(pcm, ax=ax)"
            ])
            
        return lines
    
    def _generate_vector_plot(self, ctx: Dict, plot_type: str) -> List[str]:
        lines = []
        if len(ctx['y_list']) < 3: return ["    print('Error: Need U and V columns for vector plot')"]
        u, v = self._clean_value(ctx['y_list'][1]), self._clean_value(ctx['y_list'][2])
        
        if plot_type == "Quiver":
            lines.append(f"    ax.quiver(df[{ctx['x']}], df[{ctx['y']}], df[{u}], df[{v}])")
        elif plot_type == "Barbs":
            lines.append(f"    ax.barbs(df[{ctx['x']}], df[{ctx['y']}], df[{u}], df[{v}])")
        elif plot_type == "Streamplot":
             lines.extend([
                 "    # Streamplot requires grid",
                 "    # (Assuming simple grid logic similar to contour for export brevity)",
                 "    print('Note: Streamplot export assumes data is griddable')"
             ])
        return lines
    
    def _generate_tri_plot(self, ctx: Dict, plot_type: str) -> List[str]:
        lines = []
        z = self._clean_value(ctx['y_list'][1] if len(ctx['y_list']) > 1 else None)
        
        if plot_type == "Triplot":
            lines.append(f"    ax.triplot(df[{ctx['x']}], df[{ctx['y']}])")
        elif z not in ["'None'", "None"]:
            if plot_type == "Tricontour":
                lines.append(f"    ax.tricontour(df[{ctx['x']}], df[{ctx['y']}], df[{z}], cmap={ctx['palette']})")
            elif plot_type == "Tricontourf":
                lines.extend([
                    f"    tc = ax.tricontourf(df[{ctx['x']}], df[{ctx['y']}], df[{z}], cmap={ctx['palette']})",
                    "    fig.colorbar(tc, ax=ax)"
                ])
        return lines
    
    def _generate_geospatial_plot(self, ctx: Dict) -> List[str]:
        lines = [
            "    try:",
            "        import geopandas as gpd",
            "        if 'geometry' not in df.columns:",
            "            print('Error: No geometry column found for geospatial plot')",
            "        else:",
            "            gdf = gpd.GeoDataFrame(df, geometry='geometry')"
        ]
        
        col = ctx['y'] if ctx['y'] != "None" else "None"
        scheme = self._clean_value(self._get_cfg(ctx['config'], "advanced.geospatial.scheme", "quantiles"))
        
        if col != "None":
             lines.append(f"            gdf.plot(column={col}, ax=ax, legend=True, scheme={scheme}, cmap={ctx['palette']})")
        else:
             lines.append("            gdf.plot(ax=ax)")
             
        if self._get_cfg(ctx['config'], "advanced.geospatial.axis_off"):
            lines.append("            ax.set_axis_off()")
            
        lines.extend([
            "    except ImportError:",
            "        print('Error: geopandas not installed')"
        ])
        return lines
    
    def _generate_3d_scatter(self, ctx: Dict) -> List[str]:
        lines = []
        if ctx['z'] in ["'None'", "None"]: 
            return ["    print('Error: Need Z column for 3D Scatter')"]
        
        g_marker = self._get_cfg(ctx['config'], "advanced.global_marker", {})
        size = g_marker.get('size', 6)
        kw_base = [f"s={size}**2", f"alpha={ctx['alpha']}"]
        
        marker = self._clean_value(g_marker.get('shape', 'o'))
        if marker != "'None'": kw_base.append(f"marker={marker}")
        
        if ctx['hue'] != "None":
            kw_base.append(f"cmap={ctx['palette']}")
            lines.extend([
                f"    groups = df[{ctx['hue']}].dropna().unique()",
                "    for i, group in enumerate(groups):",
                f"        mask = (df[{ctx['hue']}] == group) & df[{ctx['x']}].notna() & df[{ctx['y']}].notna() & df[{ctx['z']}].notna()",
                f"        ax.scatter3D(df.loc[mask, {ctx['x']}], df.loc[mask, {ctx['y']}], df.loc[mask, {ctx['z']}], label=str(group), {', '.join(kw_base)})"
            ])
        else:
            lines.append(f"    mask = df[{ctx['x']}].notna() & df[{ctx['y']}].notna() & df[{ctx['z']}].notna()")
            lines.append(f"    ax.scatter3D(df.loc[mask, {ctx['x']}], df.loc[mask, {ctx['y']}], df.loc[mask, {ctx['z']}], {', '.join(kw_base)})")
        return lines

    def _generate_3d_line(self, ctx: Dict) -> List[str]:
        lines = []
        if ctx['z'] in ["'None'", "None"]: 
            return ["    print('Error: Need Z column for 3D Line')"]
            
        g_line = self._get_cfg(ctx["config"], "advanced.global_line", {})
        kw_base = [
            f"linestyle={self._clean_value(g_line.get('style', '-'))}",
            f"linewidth={g_line.get('width', 1.5)}",
            f"alpha={ctx['alpha']}"
        ]
        
        if ctx['hue'] != "None":
            lines.extend([
                f"    groups = df[{ctx['hue']}].dropna().unique()",
                "    for i, group in enumerate(groups):",
                f"        mask = (df[{ctx['hue']}] == group) & df[{ctx['x']}].notna() & df[{ctx['y']}].notna() & df[{ctx['z']}].notna()",
                f"        ax.plot3D(df.loc[mask, {ctx['x']}], df.loc[mask, {ctx['y']}], df.loc[mask, {ctx['z']}], label=str(group), {', '.join(kw_base)})"
            ])
        else:
            lines.append(f"    mask = df[{ctx['x']}].notna() & df[{ctx['y']}].notna() & df[{ctx['z']}].notna()")
            lines.append(f"    ax.plot3D(df.loc[mask, {ctx['x']}], df.loc[mask, {ctx['y']}], df.loc[mask, {ctx['z']}], label=f'{{ {ctx['y']} }} vs {{ {ctx['z']} }}', {', '.join(kw_base)})")
        return lines

    def _generate_3d_surface(self, ctx: Dict) -> List[str]:
        lines = []
        if ctx['z'] in ["'None'", "None"]: 
            return ["    print('Error: Need Z column for 3D Surface')"]
            
        lines.extend([
            "    # Prepare Gridded Data for Surface",
            "    try:",
            f"        if df[[{ctx['x']}, {ctx['y']}]].duplicated().any():",
            f"            df_agg = df.groupby([{ctx['x']}, {ctx['y']}])[{ctx['z']}].mean().reset_index()",
            "        else:",
            "            df_agg = df",
            f"        piv = df_agg.pivot(index={ctx['y']}, columns={ctx['x']}, values={ctx['z']}).sort_index(axis=0).sort_index(axis=1)",
            "        X_grid, Y_grid = np.meshgrid(piv.columns.values, piv.index.values)",
            "        Z_grid = piv.values",
            f"        surf = ax.plot_surface(X_grid, Y_grid, Z_grid, cmap={ctx['palette']}, alpha={ctx['alpha']})",
            "        fig.colorbar(surf, ax=ax)",
            "    except Exception as e:",
            "        print(f'Failed to grid data for 3D Surface: {e}')"
        ])
        return lines
    
    def _generate_appearance(self, config: Dict[str, Any], x_col: str, y_cols: List[str]) -> List[str]:
        """Generate the code used for axis labels, titles, spines etc"""
        lines = ["\n    # --- 4. Appearance & Labels ---"]
        
        font_family = self._clean_value(self._get_cfg(config, 'appearance.font_family', 'Arial'))
        
        labels = {
            "title": (self._get_cfg(config, "appearance.title.text", ""), self._get_cfg(config, "appearance.title.enabled", True)),
            "xlabel": (self._get_cfg(config, "appearance.xlabel.text", x_col), self._get_cfg(config, "appearance.xlabel.enabled", True)),
            "ylabel": (self._get_cfg(config, "appearance.ylabel.text", y_cols[0] if y_cols else "Value"), self._get_cfg(config, "appearance.ylabel.enabled", True))
        }
        
        for kind, (text, enabled) in labels.items():
            if enabled:
                text_clean = self._clean_value(text)
                size = self._get_cfg(config, f"appearance.{kind}.size", 12)
                weight = self._clean_value(self._get_cfg(config, f"appearance.{kind}.weight", 'normal'))
                lines.append(f"    ax.set_{kind}({text_clean}, fontsize={size}, fontweight={weight})")
            else:
                lines.append(f"    ax.set_{kind}('')")
                
        lines.append("")
        for spine in ['top', 'bottom', 'left', 'right']:
            visible = self._get_cfg(config, f"appearance.spines.{spine}.visible", True)
            if not visible:
                lines.append(f"    ax.spines['{spine}'].set_visible(False)")
            else:
                color = self._clean_value(self._get_cfg(config, f"appearance.spines.{spine}.color", 'black'))
                width = self._get_cfg(config, f"appearance.spines.{spine}.width", 1.0)
                if color != "'black'": lines.append(f"    ax.spines['{spine}'].set_color({color})")
                if width != 1.0: lines.append(f"    ax.spines['{spine}'].set_linewidth({width})")

        return lines
    
    def _generate_axes_config(self, config: Dict[str, Any]) -> List[str]:
        """Generate scales, limits, and grids."""
        lines = ["\n    # --- 5. Axes & Grid ---"]
        
        lines.append(f"    ax.set_xscale({self._clean_value(self._get_cfg(config, 'axes.x_axis.scale', 'linear'))})")
        lines.append(f"    ax.set_yscale({self._clean_value(self._get_cfg(config, 'axes.y_axis.scale', 'linear'))})")
        
        if not self._get_cfg(config, "axes.x_axis.auto_limits", True):
             lines.append(f"    ax.set_xlim({self._get_cfg(config, 'axes.x_axis.min')}, {self._get_cfg(config, 'axes.x_axis.max')})")
        if not self._get_cfg(config, "axes.y_axis.auto_limits", True):
             lines.append(f"    ax.set_ylim({self._get_cfg(config, 'axes.y_axis.min')}, {self._get_cfg(config, 'axes.y_axis.max')})")
             
        if self._get_cfg(config, "axes.x_axis.invert"): lines.append("    ax.invert_xaxis()")
        if self._get_cfg(config, "axes.y_axis.invert"): lines.append("    ax.invert_yaxis()")

        plot_type = self._get_cfg(config, "plot_type")
        is_3d = plot_type in ["3D Scatter", "3D Line", "3D Surface"]

        if is_3d:
            if not self._get_cfg(config, "axes.z_axis.auto_limits", True):
                 lines.append(f"    ax.set_zlim({self._get_cfg(config, 'axes.z_axis.min')}, {self._get_cfg(config, 'axes.z_axis.max')})")
            if self._get_cfg(config, "axes.z_axis.invert"): lines.append("    ax.invert_zaxis()")
            
            elev = self._get_cfg(config, "appearance.viewing_angles.elevation")
            azim = self._get_cfg(config, "appearance.viewing_angles.azimuth")
            if elev is not None or azim is not None:
                lines.append(f"    ax.view_init(elev={elev}, azim={azim})")
                
            zlabel_text = self._clean_value(self._get_cfg(config, "basic.z_column", ""))
            if zlabel_text not in ["'None'", "None", "''"]:
                 lines.append(f"    ax.set_zlabel({zlabel_text})")

        if self._get_cfg(config, "grid.enabled"):
             which = self._clean_value(self._get_cfg(config, "grid.global.which", "major"))
             lines.append(f"    ax.grid(True, which={which}, alpha={self._get_cfg(config, 'grid.global.alpha', 0.5)})")
        else:
             lines.append("    ax.grid(False)")

        return lines

    def _generate_legend(self, config: Dict[str, Any]) -> List[str]:
        """Generate legend configuration."""
        lines = []
        if self._get_cfg(config, "legend.enabled", False):
            # Legend basic configuration
            custom_labels_str = self._get_cfg(config, "legend.custom_labels", "").strip()
            loc = self._clean_value(self._get_cfg(config, "legend.location", "best"))
            title = self._clean_value(self._get_cfg(config, "legend.title", ""))
            
            # Styling configuration
            fontsize = self._get_cfg(config, "legend.font_size", 10)
            title_fontsize = self._get_cfg(config, "legend.title_font_size", 12)
            ncol = self._get_cfg(config, "legend.columns", 1)
            columnspacing = self._get_cfg(config, "legend.column_spacing", 1.0)
            frameon = self._get_cfg(config, "legend.frame", True)
            fancybox = self._get_cfg(config, "legend.fancybox", True)
            shadow = self._get_cfg(config, "legend.shadow", False)
            framealpha = self._get_cfg(config, "legend.frame_alpha", 0.8)
            facecolor = self._clean_value(self._get_cfg(config, "legend.facecolor", "white"))
            edgecolor = self._clean_value(self._get_cfg(config, "legend.edgecolor", "black"))
            edgewidth = self._get_cfg(config, "legend.edge_width", 1.0)
            
            lines.extend([
                "    # Extract legend handles and labels",
                "    handles, labels = ax.get_legend_handles_labels()"
            ])
            
            if self._get_cfg(config, "basic.secondary_y_enabled"):
                lines.extend([
                    "    try:",
                    "        h2, l2 = ax2.get_legend_handles_labels()",
                    "        handles.extend(h2)",
                    "        labels.extend(l2)",
                    "    except NameError:",
                    "        pass"
                ])
                
            if custom_labels_str:
                custom_labels_list = [l.strip() for l in custom_labels_str.split(',')]
                lines.extend([
                    f"    custom_labels = {self._clean_value(custom_labels_list)}",
                    "    for i in range(min(len(labels), len(custom_labels))):",
                    "        if custom_labels[i]:",
                    "            labels[i] = custom_labels[i]"
                ])

            lines.extend([
                "    if handles:",
                "        leg_kwargs = {",
                f"            'loc': {loc},",
                f"            'title': {title},",
                f"            'fontsize': {fontsize},",
                f"            'title_fontsize': {title_fontsize},",
                f"            'ncol': {ncol},",
                f"            'columnspacing': {columnspacing},",
                f"            'frameon': {frameon},",
                f"            'fancybox': {fancybox},",
                f"            'shadow': {shadow},",
                f"            'framealpha': {framealpha},",
                f"            'facecolor': {facecolor},",
                f"            'edgecolor': {edgecolor}",
                "        }",
                "        leg = ax.legend(handles, labels, **leg_kwargs)",
                "        if leg and leg.get_frame():",
                f"            leg.get_frame().set_linewidth({edgewidth})"
            ])
            
        return lines

    def _generate_secondary_plot(self, config: Dict[str, Any], x_col: str) -> List[str]:
        """Generate code for secondary y axis"""
        lines = []
        if not self._get_cfg(config, "basic.secondary_y_enabled"):
            return lines
        
        sec_y = self._clean_value(self._get_cfg(config, "basic.secondary_y_column"))
        if sec_y in ["'None'", "None"]:
            return lines
        
        sec_type = self._get_cfg(config, "basic.secondary_plot_type", "Line")
        flip = self._get_cfg(config, "axes.flip_axes", False)
        
        lines.append("\n    # --- Secondary Axis ---")
        if flip:
            lines.append("    ax2 = ax.twiny()")
        else:
            lines.append("    ax2 = ax.twinx()")
        
        kwargs = f"label={sec_y}"
        x_data = f"df[{x_col}]"
        y_data = f"df[{sec_y}]"
        
        if sec_type == "Line":
            if flip: lines.append(f"    ax2.plot({y_data}, {x_data}, {kwargs}, linestyle='--')")
            else:    lines.append(f"    ax2.plot({x_data}, {y_data}, {kwargs}, linestyle='--')")
            
        elif sec_type == "Bar":
            if flip: lines.append(f"    ax2.barh({x_data}, {y_data}, {kwargs}, alpha=0.5, height=0.4)")
            else:    lines.append(f"    ax2.bar({x_data}, {y_data}, {kwargs}, alpha=0.5)")
            
        elif sec_type == "Scatter":
            if flip: lines.append(f"    ax2.scatter({y_data}, {x_data}, {kwargs}, marker='D')")
            else:    lines.append(f"    ax2.scatter({x_data}, {y_data}, {kwargs}, marker='D')")
            
        elif sec_type == "Area":
            if flip: lines.append(f"    ax2.fill_betweenx({x_data}, 0, {y_data}, {kwargs}, alpha=0.3)")
            else:    lines.append(f"    ax2.fill_between({x_data}, 0, {y_data}, {kwargs}, alpha=0.3)")
        
        if flip: lines.append(f"    ax2.set_xlabel({sec_y})")
        else:    lines.append(f"    ax2.set_ylabel({sec_y})")
        
        return lines
    
    def _generate_plot_code(self, df: pd.DataFrame, plot_config: Dict[str, Any]) -> str:
        """Generation of the main plotting code"""

        x_col = self._clean_value(self._get_cfg(plot_config, "basic.x_column"))
        y_cols_raw = self._get_cfg(plot_config, "basic.y_columns", [])

        if not y_cols_raw:
            y_cols_raw = []
        if isinstance(y_cols_raw, str):
            y_cols_raw = [y_cols_raw]

        y_cols_raw = [self._clean_value(c) for c in y_cols_raw if c]
        hue = self._get_cfg(plot_config, "basic.hue_column ")
        palette = self._get_cfg(plot_config, "appearance.figure.palette ", "deep ")

        lines = [
            "", 
            "def create_plot(df):", 
            "    \"\"\"Create the visualization.\"\"\""
        ]

        lines.extend(self._generate_figure_setup(plot_config))
        lines.extend(self._generate_data_prep(df, plot_config, self._get_cfg(plot_config, "basic.x_column"), y_cols_raw))
        lines.extend(self._generate_plot_dispatch(plot_config, x_col, y_cols_raw, hue, palette))
        lines.extend(self._generate_secondary_plot(plot_config, x_col))

        if self._get_cfg(plot_config, "plot_type") == "Scatter":
            get_cfg_wrapper = lambda p, d=None: self._get_cfg(plot_config, p, d)
            flip = self._get_cfg(plot_config, "axes.flip_axes", False)
            y_str = self._clean_value(y_cols_raw[0] if y_cols_raw else "None")
            lines.extend(self._generate_scatter_analysis(get_cfg_wrapper, x_col, y_str, flip))
        
        lines.extend(self._generate_appearance(plot_config, self._get_cfg(plot_config, "basic.x_column"), y_cols_raw))
        lines.extend(self._generate_axes_config(plot_config))
        lines.extend(self._generate_legend(plot_config))

        lines.extend([
            "\n    try:",
            "        fig.tight_layout()",
            "    except Exception as tight_layout_error:",
            "        print(f'Warning: tight_layout failed: {tight_layout_error}')",
            "\n    return fig, ax"
        ])
        
        return "\n".join(lines)

    def _generate_main(self, export_type: str) -> str:
        """Generates the main execution block."""
        lines = [
            "\n",
            "if __name__ == '__main__':",
            f"    print('--- {APPLICATION_NAME} Export Script ---')",
            "    # 1. Load Data",
            "    df_raw = load_data()",
            "",
            "    if df_raw is not None:",
            "        # 2. Process Data",
            "        df_processed = process_data(df_raw)",
            "        print(f'Processed data shape: {df_processed.shape}')",
            "        print('\\n', df_processed.head())",
            "",
            "        output_data_file = 'dps_processed_data.csv'",
            "        df_processed.to_csv(output_data_file, index=False)",
            "        print(f'\\nProcessed data saved to {output_data_file}')",
        ]
        
        if export_type == "Data + Plot":
            lines.extend([
                "",
                "        # 3. Create Plot",
                "        try:",
                "            fig, ax = create_plot(df_processed)",
                "            ",
                "            # 4. Save and Show Plot",
                "            output_plot_file = 'dps_exported_plot.png'",
                "            fig.savefig(output_plot_file, dpi=300, bbox_inches='tight')",
                "            print(f'\\nPlot saved to {output_plot_file}')",
                "            plt.show()",
                "            ",
                "        except Exception as e:",
                "            print(f'\\n--- PLOTTING FAILED ---')",
                "            print(f'An error occurred during plotting: {e}')",
                "            traceback.print_exc()",
            ])

        lines.extend([
            "",
            "    else:",
            "        print('Failed to load data, stopping script.')",
            "",
            "    print('--- Script execution finished ---')",
        ])
        return "\n".join(lines)

    def generate_full_script(self, 
                            df: pd.DataFrame,
                            data_filepath: str, 
                            source_info: Dict[str, Any], 
                            data_operations: List[Dict[str, Any]], 
                            plot_config: Dict[str, Any],
                            export_type: str = "Data + Plot"
                            ) -> str:
        """
        Generate complete script with both data manipulation and plotting.
        """
    
        self._add_imports(plot_config)
        
        header = self._generate_header()
        loader_func = self._generate_data_loader(data_filepath, source_info)
        processor_func = self._generate_data_ops(data_operations)
        
        plot_func = ""
        if export_type == "Data + Plot":
            plot_func = self._generate_plot_code(df, plot_config)
            
        main_block = self._generate_main(export_type)
        
        full_script = "\n\n".join(filter(None, [
            header,
            loader_func,
            processor_func,
            plot_func,
            main_block
        ]))
        
        return full_script

    def get_plot_script_only(self, df: pd.DataFrame, plot_config: Dict[str, Any]) -> str:
        """get the create_plot script for the script editor"""
        
        self._add_imports(plot_config)
        
        base_imports = [
            "import pandas as pd",
            "import numpy as np",
            "import matplotlib.pyplot as plt",
            "import seaborn as sns",
            "from matplotlib.ticker import MaxNLocator"
        ]
        self.imports.update(base_imports)

        import_block = "\n".join(sorted(list(self.imports)))
        plot_func = self._generate_plot_code(df, plot_config)

        runner_comment = (
            "\n\n# --- Internal Runner ---\n"
            "# This function is called automatically when you click 'Run Script'.\n"
            "# It expects 'df' to be available in the local scope.\n"
        )

        return f"{import_block}\n\n{plot_func}{runner_comment}"