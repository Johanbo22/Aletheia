"""
Data type chip module for visual data type of columns

This module provides the DtypeCategory enum and DtypeCategoryCreator
class to generate and cache the visual chips and icons for pandas data types
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QComboBox, QListWidget, QListWidgetItem

class DtypeCategory(StrEnum):
    """
    Enumeration of column data type categories
    """
    Integer = "integer"
    Float = "float"
    String = "string"
    Categorical = "categorical"
    Datetime = "datetime"
    Boolean = "boolean"
    Geospatial = "geospatial"
    Other = "other"

@dataclass(frozen=True)
class ChipVisualSpecification:
    """
    Visual specification of the data type chip
    Immutable

    :param label: Short text abbreviation of displayed
    :param background_color: Hexadecimal color string for the badge background
    :param text_color: Hexadecimal color string for the badge text
    :param tooltip: A longer description of the data type
    """
    label: str
    background_color: str
    text_color: str
    tooltip: str

DTYPE_SPECS: Dict[DtypeCategory, ChipVisualSpecification] = {
    DtypeCategory.Integer    : ChipVisualSpecification(
        label="#",
        background_color="#2563EB",
        text_color="#FFFFFF",
        tooltip="Integer (Numeric Whole Number)",
    ),
    DtypeCategory.Float      : ChipVisualSpecification(
        label="1.0",
        background_color="#0891B2",
        text_color="#FFFFFF",
        tooltip="Float (Numeric Decimal)",
    ),
    DtypeCategory.String     : ChipVisualSpecification(
        label="ABC",
        background_color="#16A34A",
        text_color="#FFFFFF",
        tooltip="String (Text)",
    ),
    DtypeCategory.Categorical: ChipVisualSpecification(
        label="CAT",
        background_color="#D97706",
        text_color="#FFFFFF",
        tooltip="Categorical",
    ),
    DtypeCategory.Datetime   : ChipVisualSpecification(
        label="DATE",
        background_color="#7C3AED",
        text_color="#FFFFFF",
        tooltip="Datetime (Date and Time)",
    ),
    DtypeCategory.Boolean    : ChipVisualSpecification(
        label="BOOL",
        background_color="#E11D48",
        text_color="#FFFFFF",
        tooltip="Boolean (True or False)",
    ),
    DtypeCategory.Geospatial : ChipVisualSpecification(
        label="GEO",
        background_color="#0D9488",
        text_color="#FFFFFF",
        tooltip="Geospatial (Geometry)",
    ),
    DtypeCategory.Other      : ChipVisualSpecification(
        label="OBJ",
        background_color="#64748B",
        text_color="#FFFFFF",
        tooltip="Object / Other Data",
    ),
}

class DtypeChipCreator:
    """
    Creation rulesetter for creating and caching data type icon chips
    """
    DEFAULT_WIDTH: int = 28
    DEFAULT_HEIGHT: int = 15
    DEFAULT_BORDER_RADIUS: float = 3.0
    CHIP_SIZE: QSize = QSize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

    _icon_cache: Dict[Tuple[DtypeCategory, int, int], QIcon] = {}
    _neutral_icon_cache: Dict[Tuple[str, int, int], QIcon] = {}

    @classmethod
    def get_category_for_dtype(cls, dtype: Any) -> DtypeCategory:
        """
        Identify the DtypeCategory corresponding to a pandas or Numpy data type

        :param dtype: The data type object, Series dtype or string name
        :return: The matching DtypeCategory enum value
        """
        if dtype is None:
            return DtypeCategory.Other

        if pd.api.types.is_bool_dtype(dtype):
            return DtypeCategory.Boolean

        if isinstance(dtype, pd.CategoricalDtype):
            return DtypeCategory.Categorical

        if pd.api.types.is_datetime64_any_dtype(dtype) or pd.api.types.is_timedelta64_dtype(dtype):
            return DtypeCategory.Datetime

        if pd.api.types.is_integer_dtype(dtype):
            return DtypeCategory.Integer

        if pd.api.types.is_float_dtype(dtype):
            return DtypeCategory.Float

        dtype_name: str = getattr(dtype, "name", str(dtype)).lower()
        if "geometry" in dtype_name or "geopandas" in dtype_name:
            return DtypeCategory.Geospatial

        if pd.api.types.is_string_dtype(dtype):
            return DtypeCategory.String

        if any(term in dtype_name for term in ("datetime", "timestamp", "date", "time")):
            return DtypeCategory.Datetime

        if pd.api.types.is_numeric_dtype(dtype):
            return DtypeCategory.Float

        return DtypeCategory.Other

    @classmethod
    def get_category_for_column(cls, df: Optional[pd.DataFrame], column_name: str) -> DtypeCategory:
        """
        Retrieve the DtypeCategory for a specific column in a Dataframe

        :param df: The active DataFrame
        :param column_name: The name of the column to inspect
        :return: Matching DtypeCategory enum value
        """
        if df is None or column_name not in df.columns:
            return DtypeCategory.Other

        return cls.get_category_for_dtype(df[column_name].dtype)

    @classmethod
    def get_spec_for_column(cls, df: Optional[pd.DataFrame], column_name: str) -> ChipVisualSpecification:
        """
        Retrieve the visual specification for a given DataFrame column

        :param df: The active DataFrame instance
        :param column_name: Name of the column to inspect
        :return: Visual specification of the columns data type
        """
        category: DtypeCategory = cls.get_category_for_column(df, column_name)
        return DTYPE_SPECS.get(category, DTYPE_SPECS[DtypeCategory.Other])

    @classmethod
    def get_icon(cls, category: DtypeCategory, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> QIcon:
        """
        Retrieve or generate a cached QIcon chip for the DtypeCategory

        :param category: Target DtypeCategory data type category
        :param width: Icon width in pixels
        :param height: Icon height in pixels
        :return: Rendered QIcon badge
        """
        cache_key: Tuple[DtypeCategory, int, int] = (category, width, height)
        cached_icon: Optional[QIcon] = cls._icon_cache.get(cache_key)
        if cached_icon is not None:
            return cached_icon

        spec: ChipVisualSpecification = DTYPE_SPECS.get(category, DTYPE_SPECS[DtypeCategory.Other])
        icon: QIcon = cls._render_chip(
            label=spec.label,
            bg_color_hex=spec.background_color,
            text_color_hex=spec.text_color,
            width=width,
            height=height,
        )
        cls._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def get_icon_for_column(
            cls,
            df: Optional[pd.DataFrame],
            column_name: str,
            width: int = DEFAULT_WIDTH,
            height: int = DEFAULT_HEIGHT
    ) -> QIcon:
        """
        Retrieve a cached QIcon chip for a column in a DataFrame

        :param df: Active DataFrame
        :param column_name: Column name to evaluate
        :param width: Icon width in pixels
        :param height: Icon height in pixels
        :return: Rendered QIcon badge
        """
        category: DtypeCategory = cls.get_category_for_column(df, column_name)
        return cls.get_icon(category, width, height)

    @classmethod
    def get_neutral_icon(cls, label: str = "-", width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> QIcon:
        """
        Generate a neutral placeholder icon for non-column selections

        :param label: Text displayed in the neutral badge
        :param width: Icon width in pixels
        :param height: Icon height in pixels
        :return: Rendered neutral QIcon badge
        """
        cache_key: Tuple[str, int, int] = (label, width, height)
        cached_icon: Optional[QIcon] = cls._neutral_icon_cache.get(cache_key)
        if cached_icon is not None:
            return cached_icon

        icon: QIcon = cls._render_chip(
            label=label,
            bg_color_hex="#94A3B8",
            text_color_hex="#FFFFFF",
            width=width,
            height=height,
        )
        cls._neutral_icon_cache[cache_key] = icon
        return icon

    @classmethod
    def _render_chip(
            cls,
            label: str,
            bg_color_hex: str,
            text_color_hex: str,
            width: int,
            height: int
    ) -> QIcon:
        """
        Render a rect badge onto a QPixmap and return a QIcon

        :param label: Badge text abbreviation
        :param bg_color_hex: Background color string
        :param text_color_hex: Text color hex string
        :param width: Pixel width of the badge
        :param height: Pixel height of the badge
        :return: Configured QIcon instance
        """
        pixmap: QPixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        painter.setBrush(QColor(bg_color_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            QRectF(0.0, 0.0, float(width), float(height)),
            cls.DEFAULT_BORDER_RADIUS,
            cls.DEFAULT_HEIGHT
        )

        font: QFont = QFont("Segoe UI", 7)
        font.setBold(True)
        font.setPixelSize(9)
        painter.setFont(font)
        painter.setPen(QColor(text_color_hex))

        painter.drawText(
            QRectF(0.0, 0.0, float(width), float(height)),
            Qt.AlignmentFlag.AlignCenter,
            label
        )
        painter.end()

        return QIcon(pixmap)

    @classmethod
    def sync_combobox(cls, combo: QComboBox, df: Optional[pd.DataFrame], columns: List[str],
                      prepend_items: Optional[List[str]] = None) -> None:
        """
        Populate a QCombobox with columns and prefix icons

        :param combo: The target QComboBox instance
        :param df: Active DataFrame containing column types
        :param columns: List of column name strings
        :param prepend_items: Optional items to place at the beginning of the list
        """
        current_text: str = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.setIconSize(cls.CHIP_SIZE)

        neutral_icon: QIcon = cls.get_neutral_icon()
        if prepend_items:
            for item in prepend_items:
                combo.addItem(neutral_icon, item)

        for col in columns:
            icon: QIcon = cls.get_icon_for_column(df, col)
            combo.addItem(icon, col)
            spec: ChipVisualSpecification = cls.get_spec_for_column(df, col)
            exact_dtype: str = str(df[col].dtype) if df is not None and col in df.columns else "Unknown"
            tooltip: str = f"Column: {col}\nData type: {exact_dtype} ({spec.tooltip})"
            combo.setItemData(combo.count() - 1, tooltip, Qt.ItemDataRole.ToolTipRole)

        if current_text in columns:
            combo.setCurrentText(current_text)
        elif prepend_items and current_text in prepend_items:
            combo.setCurrentText(current_text)
        elif prepend_items:
            combo.setCurrentIndex(0)
        elif columns:
            combo.setCurrentIndex(0)

        combo.blockSignals(False)

    @classmethod
    def sync_list_widget(cls, list_widget: QListWidget, df: Optional[pd.DataFrame], columns: List[str],
                         selected_items: List[str]) -> None:
        """
        Populate a QListWidget with columns and prefix icons

        :param list_widget: Target QListWidget instance
        :param df: Active DataFrame containing column types
        :param columns: List of column name strings
        :param selected_items: List of column names that must remain selected
        """
        list_widget.blockSignals(True)
        list_widget.clear()
        list_widget.setIconSize(cls.CHIP_SIZE)

        for col in columns:
            icon: QIcon = cls.get_icon_for_column(df, col)
            item: QListWidgetItem = QListWidgetItem(icon, col)
            spec: ChipVisualSpecification = cls.get_spec_for_column(df, col)
            exact_dtype: str = str(df[col].dtype) if df is not None and col in df.columns else "Unknown"
            item.setToolTip(f"Column: {col}\nData type: {exact_dtype} ({spec.tooltip})")
            list_widget.addItem(item)
            if col in selected_items:
                item.setSelected(True)

        list_widget.blockSignals(False)
