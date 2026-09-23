import re
from enum import Enum
from typing import Dict, List, Pattern, Tuple

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

class SyntaxCategory(str, Enum):
    Keyword = "Keyword"
    Builtin = "Builtin"
    Self_Cls = "Self_Cls"
    Decorator = "Decorator"
    String = "String"
    Docstring = "Docstring"
    Number = "Number"
    Function = "Function"
    ClassName = "ClassName"
    MagicMethod = "MagicMethod"
    Operator = "Operator"
    Comment = "Comment"

DefaultColorScheme: dict[SyntaxCategory, str] = {
    SyntaxCategory.Keyword    : "#ff79c6",
    SyntaxCategory.Builtin    : "#8be9fd",
    SyntaxCategory.Self_Cls   : "#ffb86c",
    SyntaxCategory.Decorator  : "#ffb86c",
    SyntaxCategory.String     : "#f1fa8c",
    SyntaxCategory.Docstring  : "#6272a4",
    SyntaxCategory.Number     : "#bd93f9",
    SyntaxCategory.Function   : "#50fa7b",
    SyntaxCategory.ClassName  : "#8be9fd",
    SyntaxCategory.MagicMethod: "#bd93f9",
    SyntaxCategory.Operator   : "#ff79c6",
    SyntaxCategory.Comment    : "#6272a4",
}

class PythonHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for Python source code

    Applies regex token formatting
    """

    def __init__(self, document: QTextDocument, color_scheme: Dict[SyntaxCategory, str] | None = None) -> None:
        """
        :param document: The parent QTextDocument to format
        :param color_scheme: Mapping of the SyntaxCategory to hex color codes.
        """
        super().__init__(document)
        self.color_scheme: Dict[SyntaxCategory, str] = color_scheme or DefaultColorScheme
        self.highlighting_rules: List[Tuple[Pattern[str], int, QTextCharFormat, SyntaxCategory]] = []
        self._setup_rules()

    def set_color_scheme(self, color_scheme: Dict[SyntaxCategory, str]) -> None:
        """
        Update the active color scheme and rehighlight the document

        :param color_scheme: New mapping of SyntaxCategory to hex color strings
        """
        self.color_scheme = color_scheme
        self._setup_rules()
        self.rehighlight()

    def _setup_rules(self) -> None:
        """
        Complies the regex and builds the syntax rule list
        """
        self.highlighting_rules.clear()

        operator_format = self._create_format(self.color_scheme[SyntaxCategory.Operator])
        operators = [
            r"=", r"\+", r"-", r"\*", r"/", r"//", r"%", r"\*\*",
            r"==", r"!=", r"<", r">", r"<=", r">=",
            r"&", r"\|", r"\^", r"~", r">>", r"<<", r":="
        ]
        self.highlighting_rules.append((
            re.compile("|".join(operators)), 0, operator_format, SyntaxCategory.Operator
        ))

        number_format = self._create_format(self.color_scheme[SyntaxCategory.Number])
        number_pattern = re.compile(
            r"\b(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|"
            r"(?:\d[\d_]*)(?:\.[\d_]+)?(?:[eE][+-]?[\d_]+)?[jJ]?)\b"
        )
        self.highlighting_rules.append((number_pattern, 0, number_format, SyntaxCategory.Number))

        func_format = self._create_format(self.color_scheme[SyntaxCategory.Function])
        self.highlighting_rules.append((
            re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()"), 0, func_format, SyntaxCategory.Function
        ))

        builtin_format = self._create_format(self.color_scheme[SyntaxCategory.Builtin])
        builtins = [
            "print", "range", "len", "list", "dict", "set", "str", "int",
            "float", "bool", "zip", "enumerate", "min", "max", "sum",
            "abs", "sorted", "tuple", "super", "isinstance", "open", "type"
        ]
        self.highlighting_rules.append((
            re.compile(r"\b(?:" + "|".join(builtins) + r")\b"), 0, builtin_format, SyntaxCategory.Builtin
        ))

        keyword_format = self._create_format(self.color_scheme[SyntaxCategory.Keyword], is_bold=True)
        keywords = [
            "def", "class", "if", "else", "elif", "while", "for", "in",
            "return", "try", "except", "import", "from", "as", "True",
            "False", "None", "and", "or", "not", "break", "continue",
            "pass", "lambda", "with", "is", "global", "raise", "yield",
            "async", "await", "match", "case"
        ]
        self.highlighting_rules.append((
            re.compile(r"\b(?:" + "|".join(keywords) + r")\b"), 0, keyword_format, SyntaxCategory.Keyword
        ))

        self_format = self._create_format(self.color_scheme[SyntaxCategory.Self_Cls], is_italic=True)
        self.highlighting_rules.append((re.compile(r"\bself\b"), 0, self_format, SyntaxCategory.Self_Cls))
        self.highlighting_rules.append((re.compile(r"\bcls\b"), 0, self_format, SyntaxCategory.Self_Cls))

        magic_format = self._create_format(self.color_scheme[SyntaxCategory.MagicMethod], is_italic=True)
        self.highlighting_rules.append((re.compile(r"\b__\w+__\b"), 0, magic_format, SyntaxCategory.MagicMethod))

        self.highlighting_rules.append(
            (re.compile(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)"), 1, func_format, SyntaxCategory.Function))

        class_format = self._create_format(self.color_scheme[SyntaxCategory.ClassName], is_bold=True)
        self.highlighting_rules.append(
            (re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"), 1, class_format, SyntaxCategory.ClassName))

        decorator_format = self._create_format(self.color_scheme[SyntaxCategory.Decorator])
        self.highlighting_rules.append((re.compile(r"@[A-Za-z0-9_.]+"), 0, decorator_format, SyntaxCategory.Decorator))

        string_format = self._create_format(self.color_scheme[SyntaxCategory.String])
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), 0, string_format, SyntaxCategory.String))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), 0, string_format, SyntaxCategory.String))

        self.multi_string_format = self._create_format(self.color_scheme[SyntaxCategory.Docstring], is_italic=True)
        self.double_multi_pattern = re.compile(r'"""')
        self.single_multi_pattern = re.compile(r"'''")

        comment_format = self._create_format(self.color_scheme[SyntaxCategory.Comment], is_italic=True)
        self.highlighting_rules.append((re.compile(r"#[^\n]*"), 0, comment_format, SyntaxCategory.Comment))

    def _create_format(self, color_hex: str, is_bold: bool = False, is_italic: bool = False) -> QTextCharFormat:
        """
        Builds a QTextCharFormat with the requested font attributes

        :param color_hex: Hexadecimal color representation
        :param is_bold: Bold font style if True
        :param is_italic: Italic font style if True
        :return: Configured QTextCharFormat object
        """
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color_hex))
        if is_bold:
            text_format.setFontWeight(QFont.Weight.Bold)
        if is_italic:
            text_format.setFontItalic(True)
        return text_format

    def highlightBlock(self, text: str) -> None:
        """
        Applies syntax highlighting rules and block states across a line of text

        :param text: Current block of text to evaluate
        """
        string_intervals: list[tuple[int, int]] = []
        for pattern, group_index, text_format, category in self.highlighting_rules:
            for expression_match in pattern.finditer(text):
                start_index = expression_match.start(group_index)
                match_length = expression_match.end(group_index) - start_index

                if start_index < 0 or match_length <= 0:
                    continue

                if category == SyntaxCategory.Comment:
                    in_string = any(s_start <= start_index < s_end for s_start, s_end in string_intervals)
                    if in_string:
                        continue

                self.setFormat(start_index, match_length, text_format)
                if category == SyntaxCategory.String:
                    string_intervals.append((start_index, start_index + match_length))

        default_state: int = 0
        self.setCurrentBlockState(default_state)

        double_qoute_multiline_state: int = 1
        self._highlight_multiline(text, double_qoute_multiline_state, self.double_multi_pattern, string_intervals)

        single_quote_multiline_state: int = 2
        if self.currentBlockState() == default_state:
            self._highlight_multiline(text, single_quote_multiline_state, self.single_multi_pattern, string_intervals)

    def _highlight_multiline(self, text: str, state_id: int, delimiter_pattern: re.Pattern[str],
                             string_intervals: list[tuple[int, int]]) -> None:
        """
        Processes and styles multiline docstrings

        :param text: Text block content
        :param state_id: Integer identifier representing the active delimiter state
        :param delimiter_pattern: Compiled regex matching triple qoute marks
        :param string_intervals: Spans of single-line strings to avoid false triggers
        """
        start_index: int = 0
        search_offset: int = 0

        if self.previousBlockState() == state_id:
            start_index = 0
            search_offset = 0
        else:
            match = None
            for candidate in delimiter_pattern.finditer(text):
                if not any(s_start <= candidate.start() < s_end for s_start, s_end in string_intervals):
                    match = candidate
                    break
            start_index = match.start() if match else -1
            search_offset = 3

        while start_index >= 0:
            match = delimiter_pattern.search(text, start_index + search_offset)
            if match:
                end_index: int = match.start()
                match_length: int = end_index - start_index + 3
                self.setFormat(start_index, match_length, self.multi_string_format)

                next_match = None
                for candidate in delimiter_pattern.finditer(text, start_index + match_length):
                    if not any(s_start <= candidate.start() < s_end for s_start, s_end in string_intervals):
                        next_match = candidate
                        break

                start_index = next_match.start() if next_match else -1
                search_offset = 3
            else:
                self.setCurrentBlockState(state_id)
                self.setFormat(start_index, len(text) - start_index, self.multi_string_format)
                break
