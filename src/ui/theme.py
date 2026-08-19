from PyQt6.QtGui import QColor

class ThemeColors:
    """
    Central config for Aletheia theme colors
    """
    
    # Border colors
    BORDER_BASE = QColor("#a0a0a0")
    BORDER_HOVER = QColor("#707070")
    BORDER_FOCUS = QColor("#1976D2")
    
    # Widget overrides
    RADIO_BORDER_BASE = QColor("#777777")
    LIST_BORDER_BASE = QColor("#c2c2c2")
    SLIDER_GROOVE_BORDER = QColor("#c2c2c2")
    
    # Text colors
    TEXT_PRIMARY = QColor("#333333")
    TEXT_DISABLED = QColor("#a0a0a0")
    
    # Background colors
    BG_WHITE = QColor("#ffffff")
    BG_LIGHT_GRAY = QColor("#f0f0f0")
    
    # Indicators
    ACCENT_COLOR = BORDER_FOCUS
    
    # Text for information
    InfoStylesheet = "color: #666; font-style: italic; font-size: 9pt;"
    WarningInfoStylesheet = "color: #ff6b35; font-style: italic; font-size: 9pt;"
    MutedTextStylesheet = "color: #7f8c8d; font-size: 9pt; font-style: italic;"
    
    # Status labels
    SuccessStatusStylesheet = "color: #27ae60; font-weight: bold; padding: 5px; background-color: #ecf0f1; border-radius: 3px;"
    WarningStatusStylesheet = "color: #e74c3c; font-weight: bold; padding: 5px; background-color: #ffe5e5; border-radius: 3px;"
    
    # Headers
    SectionHeaderStylesheet = "font-weight: bold; color: #2c3e50; font-size: 11pt; margin-bottom: 5px;"
    GroupBoxHeaderStyle = "AnimatedGroupBox { font-size: 14pt; font-weight: bold;}"
    GroupBoxHeaderLargeStyle = "AnimatedGroupBox { font-size: 16pt; font-weight: bold;}"
    HelpBoxStylesheet = "background-color: #f0f0f0; padding: 8px; border-radius: 4px; margin-top: 10px;"
    
    # Button color
    MainColor = "#2196F3"
    DestructiveColor = "#E74C3C"
    ButtonDefaultColor = "#ededed"
    