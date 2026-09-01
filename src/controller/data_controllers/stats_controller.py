import base64
import html
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PyQt6.QtWidgets import QInputDialog

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.core.resource_loader import get_resource_path
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

class StatsController(BaseDataController):
    """
    Sub-controller for handling Statistical Testing routing and results generation
    """

    def run_statistical_test_from_selection(self) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        _, selected_columns = self.view.get_selection_state()

        if len(selected_columns) == 2:
            col1, col2 = selected_columns
            if not pd.api.types.is_numeric_dtype(self.data_handler.df[col1]) or \
                    not pd.api.types.is_numeric_dtype(self.data_handler.df[col2]):
                global_signals.request_toast(
                    "Warning", "Both selected columns must be numeric", ToastLevel.WARNING
                )
                self._render_test_results_page()
                return

            test_type, ok = QInputDialog.getItem(
                self.view, "Select Statistical Test", f"Select test to run between '{col1}' and '{col2}':",
                ["pearson", "t-test", "anova"], 0, False
            )
            if ok and test_type:
                self._execute_statistical_test(col1, col2, test_type)
        else:
            self._render_test_results_page()

    def _execute_statistical_test(self, col1: str, col2: str, test_type: str) -> None:
        if self.data_handler.df is None:
            return

        try:
            results = self.data_handler.run_statistical_test(test_type, col1, col2)
            stat_val, p_val = results['statistic'], results['p_value']
            test_name, interpretation = results['test'], results['interpretation']

            fig, ax = plt.subplots(figsize=(6, 4))
            if test_type == "pearson":
                ax.scatter(self.data_handler.df[col1], self.data_handler.df[col2], alpha=0.6, color='#3b82f6')
                ax.set_xlabel(col1)
                ax.set_ylabel(col2)
                ax.set_title(f"Scatter Plot: {col1} vs {col2}", fontsize=10)
            else:
                data_to_plot = [self.data_handler.df[col1].dropna(), self.data_handler.df[col2].dropna()]
                bplot = ax.boxplot(data_to_plot, patch_artist=True, labels=[col1, col2])
                for patch in bplot['boxes']:
                    patch.set_facecolor('#eff6ff')
                    patch.set_edgecolor('#3b82f6')
                for median in bplot['medians']:
                    median.set_color('#1e3a8a')
                ax.set_ylabel("Values")
                ax.set_title(f"Distribution Comparison: {col1} vs {col2}", fontsize=10)

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=100, transparent=True)
            plt.close(fig)
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            img_html = f'<img src="data:image/png;base64,{img_str}" alt="Statistical Graph" style="max-width: 100%; height: auto; display: block; margin: 0 auto;"/>'

            if not hasattr(self.data_handler, "test_results_history"):
                self.data_handler.test_results_history = []

            is_significant = p_val < 0.05
            badge_class = "badge-significant" if is_significant else "badge-insignificant"
            badge_text = "Significant (p < 0.05)" if is_significant else "Not Significant"

            p_val_str = f"{p_val:.4e}" if p_val < 0.0001 else f"{p_val:.4f}"

            raw_clipboard = (
                f"Test: {test_name}\n"
                f"Columns: {col1} vs {col2}\n"
                f"Test Statistic: {stat_val:.4f}\n"
                f"P-Value: {p_val_str}\n"
                f"Interpretation: {interpretation}"
            )
            clipboard_text = html.escape(raw_clipboard).replace('\n', '&#10;')

            html_result = f"""
                            <div class="test-card" data-pvalue="{p_val}" data-timestamp="{len(self.data_handler.test_results_history)}">
                                <div class="card-header-row">
                                    <h3>{test_name}</h3>
                                    <div class="header-actions">
                                        <span class="sig-badge {badge_class}">{badge_text}</span>
                                        <button class="copy-btn" title="Copy to clipboard" data-clipboard="{clipboard_text}">
                                            &#x2398; Copy
                                        </button>
                                        <button class="dismiss-btn" title="Remove this result">&times;</button>
                                    </div>
                                </div>
                                <div class="test-content">
                                    <p class="compare-text"><b>Compared Columns:</b> <span>{col1}</span> vs <span>{col2}</span></p>
                                    <div class="metrics-container">
                                        <div class="metric-box">
                                            <div class="metric-label">Test Statistic</div>
                                            <div class="metric-value">{stat_val:.4f}</div>
                                        </div>
                                        <div class="metric-box">
                                            <div class="metric-label">P-Value</div>
                                            <div class="metric-value">{p_val_str}</div>
                                        </div>
                                    </div>
                                    <div class="interpretation-box">
                                        <b class="interpretation-label">Interpretation</b><br>
                                        <div style="margin-top: 6px;">{interpretation}</div>
                                    </div>
                                    <div class="visual-sub-card">
                                        <h4 class="sub-card-header"><span class="sub-toggle-icon">&#9658;</span> Visual Distribution</h4>
                                        <div class="sub-card-content" style="display: none;">
                                            {img_html}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """
            self.data_handler.test_results_history.insert(0, html_result)
            self.status_bar.log(f"Ran {test_name} on '{col1}' and '{col2}' (p={p_val_str})", LogLevel.SUCCESS)

            self._render_test_results_page()
        except Exception as StatisticalTestError:
            global_signals.request_toast(
                "Error", f"Failed to run statistical test", ToastLevel.ERROR
            )
            self.status_bar.log(f"Statistical test failed: {str(StatisticalTestError)}", LogLevel.ERROR)
            self._render_test_results_page()

    def _render_test_results_page(self) -> None:
        if not hasattr(self, "stats_page_attached"):
            self.stats_page_attached = True

        css_path = Path(get_resource_path("../resources/test_resultPanel/stats_test_style.css"))
        js_path = Path(get_resource_path("../resources/test_resultPanel/stats_test_script.js"))

        css_content = css_path.read_text(encoding="UTF-8") if css_path.exists() else ""
        js_content = js_path.read_text(encoding="UTF-8") if js_path.exists() else ""

        history = getattr(self.data_handler, "test_results_history", [])

        full_page = f"""<!DOCTYPE html>
                                <html>
                                <head>
                                    <meta charset="UTF-8">
                                    <style>
                                        {css_content}
                                    </style>
                                    <script>
                                        {js_content}
                                    </script>
                                </head>
                                <body>
                                    <div class="page-header">
                                        <h2>Statistical Analysis Results</h2>
                                        <div class="controls-row">
                                            <input type="text" id="testSearch" class="search-box" placeholder="Search tests, columns, or results...">
                                            <select id="sortSelect" class="sort-dropdown">
                                                <option value="newest">Sort: Newest First</option>
                                                <option value="pvalue">Sort: Most Significant (P-Value)</option>
                                                <option value="type">Sort: Test Type</option>
                                            </select>
                                            <button id="expandAllBtn" class="global-control-btn">Expand All</button>
                                            <button id="collapseAllBtn" class="global-control-btn">Collapse All</button>
                                        </div>
                                    </div>
                                    <div id="test-list">
                                        {"".join(history)}
                                    </div>
                                </body>
                                </html>
                                """

        self.view.test_results_text.setHtml(full_page)
        self.view.data_tabs.setCurrentWidget(self.view.test_results_text)
