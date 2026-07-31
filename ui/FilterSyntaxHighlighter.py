import re
from typing import List

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

class FilterSyntaxHighlighter(QSyntaxHighlighter):
    """
    Highlights syntax for filter expressions
    """

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.column_names = []

        self.operator_format = QTextCharFormat()
        self.operator_format.setFontWeight(QFont.Weight.Bold)
        self.operator_format.setForeground(QColor("#d32f2f"))

        self.column_format = QTextCharFormat()
        self.column_format.setFontItalic(True)
        self.column_format.setForeground(QColor("#1976d2"))

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#388e3c"))

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#f57c00"))

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        self.keyword_format.setForeground(QColor("#7b1fa2"))

        self.keywords = ["True", "False", "None", "NaN", "is", "in", "and", "or", "not"]

        operators = [
            "==", "!=", "<=", ">=", "<", ">", "&", "|", "~"
        ]
        self.operator_patterns = [re.escape(op).strip() for op in operators]

        self.string_pattern = re.compile(r'("[^"\\]*(\\.[^"\\]*)*"|\'[^\'\\]*(\\.[^\'\\]*)*\')')
        self.number_pattern = re.compile(r'\b[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b')
        self.function_pattern = re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\()')

    def set_columns(self, columns: List[str]) -> None:
        """Sets the valid column names to highlight and re-evaluate highlighting"""
        self.column_names = columns
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Applies the syntax highlighting to the block of text"""
        for keyword in self.keywords:
            pattern = r'\b' + keyword + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

        for match in self.function_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

        for pattern in self.operator_patterns:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.operator_format)

        for col in sorted(self.column_names, key=len, reverse=True):
            is_alnum = col.replace("_", "").isalnum()
            pattern = r'\b' + re.escape(col) + r'\b' if is_alnum else re.escape(col)
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.column_format)

        for match in self.number_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)

        for match in self.string_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)
