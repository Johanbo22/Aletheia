# ui/dialogs/OutlierDetectionDialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QMessageBox, QInputDialog, QWidget, QSplitter, QHeaderView, QApplication, QSpinBox, QGroupBox, QDoubleSpinBox, QComboBox, QPushButton
from PyQt6.QtCore import Qt, QTimer

from core.data_handler import DataHandler
from ui.theme import ThemeColors
from ui.data_table_model import DataTableModel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


try:
    from scipy import stats
except ImportError:
    stats = None


class OutlierDetectionDialog(QDialog):
    def __init__(self, data_handler: DataHandler, method="z_score", parent=None):
        super().__init__(parent)
        self.data_handler: DataHandler = data_handler
        self.method = method
        self.outlier_indices = []
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(400)
        self.debounce_timer.timeout.connect(self.apply_detection)

        self.setWindowTitle(
            f"Outlier Detection Tool - {method.replace('_', ' ').title()}"
        )
        self.resize(900, 750)
        
        self.numeric_columns = self.data_handler.df.select_dtypes(include=["number"]).columns.tolist()
        
        if not self.numeric_columns:
            QMessageBox.warning(self, "No numeric data", "The current dataset contains no numeric columns")
            QTimer.singleShot(0, self.reject)
            return
        
        self.init_ui()
        self.apply_detection()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # This is a settings panel
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout()

        # Controls to chose methods and columns
        self.numeric_columns = self.data_handler.df.select_dtypes(
            include=["number"]
        ).columns.tolist()

        settings_layout.addWidget(QLabel("Target Column(s):"))
        self.column_combo = QComboBox()
        self.column_combo.addItems(self.numeric_columns)

        if self.method == "isolation_forest":
            self.column_combo.addItem("All Numeric Columns")
            self.column_combo.setCurrentText("All Numeric Columns")

        self.column_combo.currentTextChanged.connect(self.apply_detection)
        settings_layout.addWidget(self.column_combo)

        if self.method == "z_score":
            settings_layout.addWidget(QLabel("Threshold (Standard Deviation):"))
            self.parameter_spin = QDoubleSpinBox()
            self.parameter_spin.setRange(1.0, 10.0)
            self.parameter_spin.setValue(3.0)
            self.parameter_spin.setSingleStep(0.1)
            self.parameter_spin.setSuffix(" σ")
            self.parameter_spin.setToolTip("Number of standard deviations from the mean to define an outlier")
            self.parameter_spin.valueChanged.connect(self.debounce_timer.start)
            settings_layout.addWidget(self.parameter_spin)

        elif self.method == "iqr":
            settings_layout.addWidget(QLabel("IQR Multiplier:"))
            self.parameter_spin = QDoubleSpinBox()
            self.parameter_spin.setRange(0.5, 5.0)
            self.parameter_spin.setValue(1.5)
            self.parameter_spin.setSingleStep(0.1)
            self.parameter_spin.setSuffix(" x")
            self.parameter_spin.setToolTip("Multiplier for the Interquartile Range to create upper and lower bounds")
            self.parameter_spin.valueChanged.connect(self.debounce_timer.start)
            settings_layout.addWidget(self.parameter_spin)

        elif self.method == "isolation_forest":
            settings_layout.addWidget(QLabel("Contamination:"))
            self.parameter_spin = QDoubleSpinBox()
            self.parameter_spin.setRange(0.01, 0.5)
            self.parameter_spin.setValue(0.05)
            self.parameter_spin.setSingleStep(0.01)
            self.parameter_spin.setToolTip("Expected proportion of outliers in the dataset")
            self.parameter_spin.valueChanged.connect(self.debounce_timer.start)
            settings_layout.addWidget(self.parameter_spin)

        refresh_button = QPushButton("Recalculate")
        refresh_button.setObjectName("MainActionButton")
        refresh_button.clicked.connect(self.apply_detection)
        settings_layout.addWidget(refresh_button)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # INfo
        self.info_label = QLabel("Ready")
        self.info_label.setObjectName("outlier_info_label")
        self.info_label.setProperty("state", "normal")
        layout.addWidget(self.info_label)
        
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # Plot area for visualization
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        plot_group = QGroupBox("Distribution")
        group_plot_layout = QVBoxLayout()
        
        # Plot Controls
        plot_controls_layout = QHBoxLayout()
        plot_controls_layout.addWidget(QLabel("Bins"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(5, 200)
        self.bins_spin.setValue(30)
        self.bins_spin.setToolTip("Number of bins used in the histogram")
        self.bins_spin.valueChanged.connect(self.on_bins_changed)
        plot_controls_layout.addWidget(self.bins_spin)
        plot_controls_layout.addStretch()
        group_plot_layout.addLayout(plot_controls_layout)
        
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.figure.patch.set_facecolor("#2b2b2b")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setObjectName("outlier_canvas_container")
        
        group_plot_layout.addWidget(self.canvas)
        plot_group.setLayout(group_plot_layout)
        plot_layout.addWidget(plot_group)
        
        main_splitter.addWidget(plot_widget)
        
        # The Preview tabelks
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setObjectName("MainDataHeader")
        self.table_view.verticalHeader().setObjectName("MainDataHeader")
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        main_splitter.addWidget(self.table_view)
        
        main_splitter.setSizes([400, 350])
        layout.addWidget(main_splitter, stretch=1)

        # Action buttons
        button_layout = QHBoxLayout()
        
        self.flag_button = QPushButton("Flag Outliers")
        self.flag_button.clicked.connect(self.flag_outliers)
        self.flag_button.setToolTip("Create a new column marking outliers as True")
        button_layout.addWidget(self.flag_button)

        self.remove_button = QPushButton("Remove Outliers")
        self.remove_button.setObjectName("DestructiveButton")
        self.remove_button.clicked.connect(self.remove_outliers)
        button_layout.addWidget(self.remove_button)

        # Clippin contrsol
        self.clip_button = QPushButton("Clip Values")
        self.clip_button.setObjectName("MainActionButton")
        self.clip_button.clicked.connect(self.clip_outliers)
        if self.method == "isolation_forest":
            self.clip_button.setEnabled(False)
            self.clip_button.setToolTip(
                "Clipping is not available for Isolation Forest"
            )
        button_layout.addWidget(self.clip_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def apply_detection(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            selected_col_text = self.column_combo.currentText()
            columns = (
                self.numeric_columns
                if selected_col_text == "All Numeric Columns"
                else [selected_col_text]
            )

            param = self.parameter_spin.value()
            kwargs = {}

            if self.method == "z_score":
                kwargs["threshold"] = param
            if self.method == "iqr":
                kwargs["multiplier"] = param
            if self.method == "isolation_forest":
                kwargs["contamination"] = param

            self.outlier_indices = self.data_handler.detect_outliers(
                self.method, columns, **kwargs
            )

            self.model = DataTableModel(
                self.data_handler, highlighted_rows=self.outlier_indices
            )
            self.table_view.setModel(self.model)
            outlier_count = len(self.outlier_indices)
            self.info_label.setText(f"Found {outlier_count} outliers.")
            
            self.info_label.setProperty("state", "warning" if outlier_count > 0 else "success")
            self.info_label.style().unpolish(self.info_label)
            self.info_label.style().polish(self.info_label)
            
            has_outliers = outlier_count > 0
            self.flag_button.setEnabled(has_outliers)
            self.remove_button.setEnabled(has_outliers)
            if self.method != "isolation_forest":
                self.clip_button.setEnabled(has_outliers)

            self.update_plot(columns, param)

        except Exception as ApplyOutlierDetectionError:
            self.info_label.setText(
                f"ApplyOutlierDetectionError: {str(ApplyOutlierDetectionError)}"
            )
            self.info_label.setProperty("state", "error")
            self.info_label.style().unpolish(self.info_label)
            self.info_label.style().polish(self.info_label)
            
            self.outlier_indices = []
            self.flag_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.clip_button.setEnabled(False)
        finally:
            QApplication.restoreOverrideCursor()

    def on_bins_changed(self) -> None:
        """Refreshes the plot when bin count is change"""
        selected_col_text = self.column_combo.currentText()
        columns = (
            self.numeric_columns
            if selected_col_text == "All Numeric Columns"
            else [selected_col_text]
        )
        param = self.parameter_spin.value()
        self.update_plot(columns, param)

    def update_plot(self, columns: list[str], param: float) -> None:
        """Updates the distribution plot"""
        self.figure.clear()

        if len(columns) != 1:
            ax = self.figure.add_subplot(111)
            ax.text(
                0.5,
                0.5,
                "Visualization available for a single column selection",
                ha="center",
                va="center",
                color="white",
            )
            ax.set_facecolor("#2b2b2b")
            self.canvas.draw()
            return

        col_name = columns[0]
        data = self.data_handler.df[col_name]
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            data = data.iloc[:, 0]
        
        data = data.dropna()

        if data.empty:
            return

        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#2b2b2b")
        ax.tick_params(colors="white")
        ax.spines["bottom"].set_color("white")
        ax.spines["left"].set_color("white")
        ax.spines["right"].set_color("#2b2b2b")
        ax.spines["top"].set_color("#2b2b2b")

        # Histogram drawing
        bins_count = self.bins_spin.value()
        n, bins, patches = ax.hist(
            data, bins=bins_count, color="#3498db", alpha=0.7, edgecolor="#2b2b2b"
        )
        ax.grid(True, linestyle=":", alpha=0.3, color="white", zorder=0)

        lower_bound, upper_bound = None, None
        if self.method == "z_score" and stats:
            mean = data.mean()
            std = data.std()
            upper_bound = mean + param * std
            lower_bound = mean - param * std
            title = f"Z-Score Distribution with a threshold: {param:.4f}σ"

        elif self.method == "iqr":
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - param * IQR
            upper_bound = Q3 + param * IQR
            title = f"IQR Distribution with Multiplier: {param:.4f})"
        else:
            title = f"Distribution: {col_name}"

        xlims = ax.get_xlim()
        # Draw threshold lines
        if lower_bound is not None:
            ax.axvline(
                lower_bound,
                color="#e74c3c",
                linestyle="--",
                linewidth=2,
                label="Lower Bound",
                zorder=4
            )
            ax.axvspan(xlims[0], lower_bound, color="#e74c3c", alpha=0.15, zorder=1)
            
        if upper_bound is not None:
            ax.axvline(
                upper_bound,
                color="#e74c3c",
                linestyle="--",
                linewidth=2,
                label="Upper Bound",
                zorder=4
            )
            ax.axvspan(upper_bound, xlims[1], color="#e74c3c", alpha=0.15, zorder=1)
        
        ax.set_xlim(xlims)

        ax.set_title(title, color="white", pad=10)

        if lower_bound is not None or upper_bound is not None:
            legend = ax.legend(facecolor="#2b2b2b", edgecolor="white")
            for text in legend.get_texts():
                text.set_color("white")

        self.figure.tight_layout()
        self.canvas.draw()

    def clip_outliers(self) -> None:
        """Clip outliers to a calculated threshold instead of removing rows"""
        if not self.outlier_indices and self.method != "isolation_forest":
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clipping",
            "Are you sure you want to clip values in the selected column(s)?\nValues outside the threshold will be set to the threshold limit.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            selected_col_text = self.column_combo.currentText()
            columns = (
                self.numeric_columns
                if selected_col_text == "All Numeric Columns"
                else [selected_col_text]
            )
            param = self.parameter_spin.value()

            self.data_handler.clean_data(
                "clip_outliers",
                method=self.method,
                columns=columns,
                threshold=param if self.method == "z_score" else None,
                multiplier=param if self.method == "iqr" else None,
            )
            self.accept()

    def remove_outliers(self) -> None:
        if not self.outlier_indices:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove: {len(self.outlier_indices)} rows from the current dataset?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.data_handler.clean_data("remove_rows", rows=self.outlier_indices)
            self.accept()
    
    def flag_outliers(self) -> None:
        """Flags detected outliers in a new column as True"""
        if not self.outlier_indices:
            return
        
        name, ok = QInputDialog.getText(self, "Flag Outliers", "Enter name for the new column:", text="is_outlier")
        if ok and name:
            try:
                self.data_handler.clean_data("flag_outliers", rows=self.outlier_indices, new_column_name=name)
                self.accept()
            except Exception as error:
                QMessageBox.critical(self, "Error", f"Failed to flag outliers: {str(error)}")
