from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from typing import List, Tuple, Pattern, Dict
import re
from enum import Enum

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

DefaultColorScheme: Dict[SyntaxCategory, str] = {
    SyntaxCategory.Keyword: "#ff79c6",
    SyntaxCategory.Builtin: "#8be9fd",
    SyntaxCategory.Self_Cls: "#ffb86c",
    SyntaxCategory.Decorator: "#ffb86c",
    SyntaxCategory.String: "#f1fa8c",
    SyntaxCategory.Docstring: "#6272a4",
    SyntaxCategory.Number: "#bd93f9",
    SyntaxCategory.Function: "#50fa7b",
    SyntaxCategory.ClassName: "#8be9fd",
    SyntaxCategory.MagicMethod: "#bd93f9",
    SyntaxCategory.Operator: "#ff79c6",
    SyntaxCategory.Comment: "#6272a4"
}

class PythonHighlighter(QSyntaxHighlighter):
    """Simple syntax highligher for Python code"""

    def __init__(self, document: QTextDocument, color_scheme: Dict[SyntaxCategory, str] | None = None) -> None:
        super().__init__(document)
        self.color_scheme: Dict[SyntaxCategory, str] = color_scheme or DefaultColorScheme
        self.highlighting_rules: List[Tuple[Pattern[str], QTextCharFormat]] = []
        self._setup_rules()
    
    def set_color_scheme(self, color_scheme: Dict[SyntaxCategory, str]) -> None:
        self.color_scheme = color_scheme
        self._setup_rules()
        self.rehighlight()
    
    def _setup_rules(self) -> None:
        self.highlighting_rules.clear()

        #keywords
        keyword_format = self._create_format(self.color_scheme[SyntaxCategory.Keyword], is_bold=True)
        keywords = [
            "def", "class", "if", "else", "elif", "while", "for", "in",
            "return", "try", "except", "import", "from", "as", "True",
            "False", "None", "and", "or", "not", "break", "continue",
            "pass", "lambda", "with", "is", "global", "raise", "yield", 
            "async", "await", "match", "case"
        ]
        self.highlighting_rules.append((re.compile(r'\b(?:' + '|'.join(keywords) + r')\b'), 0, keyword_format))
        
        # Builtin functions
        builtin_format = self._create_format(self.color_scheme[SyntaxCategory.Builtin])
        builtins = [
            "print", "range", "len", "list", "dict", "set", "str", "int",
            "float", "bool", "zip", "enumerate", "min", "max", "sum",
            "abs", "sorted", "tuple", "super", "isinstance", "open", "type"
        ]
        self.highlighting_rules.append((re.compile(r'\b(?:' + '|'.join(builtins) + r')\b'), 0, builtin_format))

        # self and cls
        self_format = self._create_format(self.color_scheme[SyntaxCategory.Self_Cls], is_italic=True)
        self.highlighting_rules.append((re.compile(r"\bself\b"), 0, self_format))
        self.highlighting_rules.append((re.compile(r"\bcls\b"), 0, self_format))
        
        # magic methods
        magic_format = self._create_format(self.color_scheme[SyntaxCategory.MagicMethod], is_italic=True)
        self.highlighting_rules.append((re.compile(r"\b__\w+__\b"), 0, magic_format))
        
        # class names
        class_format = self._create_format(self.color_scheme[SyntaxCategory.ClassName], is_bold=True)
        self.highlighting_rules.append((re.compile(r"\bclass\s+(\w+)"), 1, class_format))

        # decorators
        decorator_format = self._create_format(self.color_scheme[SyntaxCategory.Decorator])
        self.highlighting_rules.append((re.compile(r"@[A-Za-z0-9_\.]+"), 0, decorator_format))
        
        # functions
        func_format = self._create_format(self.color_scheme[SyntaxCategory.Function])
        self.highlighting_rules.append((re.compile(r"\bdef\s+(\w+)"), 1, func_format))
        self.highlighting_rules.append((re.compile(r"\b[A-Za-z0-9_]+(?=\()"), 0, func_format))
        
        # numbers
        number_format = self._create_format(self.color_scheme[SyntaxCategory.Number])
        self.highlighting_rules.append((re.compile(r"\b(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|0[oO][0-7]+|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\b"), 0, number_format))

        # strings
        string_format = self._create_format(self.color_scheme[SyntaxCategory.String])
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), 0, string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), 0, string_format))
        
        # multi line strings
        self.multi_string_format = self._create_format(self.color_scheme[SyntaxCategory.Docstring], is_italic=True)
        self.double_multi_pattern = re.compile(r'"""')
        self.single_multi_pattern = re.compile(r"'''")

        # comment
        comment_format = self._create_format(self.color_scheme[SyntaxCategory.Comment], is_italic=True)
        self.highlighting_rules.append((re.compile(r"#[^\n]*"), 0, comment_format))
    
    def _create_format(self, color_hex: str, is_bold: bool = False, is_italic: bool = False) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color_hex))
        if is_bold:
            text_format.setFontWeight(QFont.Weight.Bold)
        if is_italic:
            text_format.setFontItalic(True)
        return text_format
        
    def highlightBlock(self, text: str) -> None:
        """
        Applies syntax highlighting for a single block of text,\n
        including multi line strings
        """
        for pattern, group_index, text_format in self.highlighting_rules:
            expression_match = pattern.search(text)
            while expression_match:
                start_index = expression_match.start(group_index)
                match_length = expression_match.end(group_index) - start_index
                if start_index >= 0 and match_length > 0:
                    self.setFormat(start_index, match_length, text_format)
                
                expression_match = pattern.search(text, expression_match.end())
        
        default_state: int = 0
        self.setCurrentBlockState(default_state)
        
        double_quote_multiline_state: int = 1
        self._highlight_multiline(text, double_quote_multiline_state, self.double_multi_pattern)
        
        single_quote_multiline_state: int = 2
        if self.currentBlockState() == default_state:
            self._highlight_multiline(text, single_quote_multiline_state, self.single_multi_pattern)
    
    def _highlight_multiline(self, text: str, state_id: int, delimiter_pattern: re.Pattern) -> None:
        start_index: int = 0
        
        if self.previousBlockState() == state_id:
            start_index = 0
        else:
            match = delimiter_pattern.search(text)
            start_index = match.start() if match else -1
        
        while start_index >= 0:
            match = delimiter_pattern.search(text, start_index + 3)
            if match:
                end_index = match.start()
                match_length = end_index - start_index + 3
                self.setFormat(start_index, match_length, self.multi_string_format)
                
                next_match = delimiter_pattern.search(text, start_index + match_length)
                start_index = next_match.start() if next_match else -1
            else:
                self.setCurrentBlockState(state_id)
                self.setFormat(start_index, len(text) - start_index, self.multi_string_format)
                break