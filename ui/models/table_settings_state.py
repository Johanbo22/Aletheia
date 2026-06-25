from dataclasses import dataclass, field

@dataclass
class TableSettingsState:
    """The visual configurations state for the DataTableModel"""
    precision: int = 2
    formatting_rules: list = field(default_factory=list)
    render_bools: bool = True
    nan_display: str = "NaN"
    thousands_sep: bool = False
    scientific_notation: bool = False
    grid_style: str = "Solid Line"
    grid_color: str = "#D3D3D3"
    text_alignment: str = "Left"
