"""
Filter Query Parser module to translate a text expression into GUI rulesets

An AST parser for the FilterAdvancedDialog, SubsetDialog
Made to allow for transverse operations in text view and GUI view.
"""

import ast
import re
from dataclasses import dataclass
from typing import Sequence

from src.core.subset_manager import FilterCondition, FilterLogic

FilterScalar = str | int | float | None

class FilterQueryParseError(ValueError):
    """Raised when a filter query string cannot be translated into the GUI rules"""

@dataclass(frozen=True)
class ParsedFilterRule:
    """Immutable specification for a single filter rule in the GUI row"""
    operator: str | None
    column: str
    condition: str
    value: FilterScalar

class FilterQueryParser:
    """
    Translates a text filter expression into a sequence of ParsedFilterRules
    """
    __placeholder_prefix: str = "__col_placeholder_"

    def __init__(self, valid_columns: Sequence[str]) -> None:
        self._valid_columns: list[str] = list(valid_columns)
        self._col_lookup: dict[str, str] = {}

    def parse(self, query: str) -> list[ParsedFilterRule]:
        """Parse a raw filter query string into a list of ParsedFilterRule items"""
        cleaned_query: str = query.strip()
        if not cleaned_query:
            raise FilterQueryParseError("Please enter a filter query to translate")

        sanitized_query: str = self._preprocess_query(cleaned_query)

        try:
            tree: ast.Expression = ast.parse(sanitized_query, mode="eval")
        except SyntaxError as exc:
            raise FilterQueryParseError(f"Invalid query syntax: {exc.msg}") from exc

        return self._extract_flat_rules(tree.body, sanitized_query)

    def _preprocess_query(self, query: str) -> str:
        """Replace any backticked column names and bitwise operands with Python AST values"""
        self._col_lookup.clear()
        counter: int = 0

        def replace_backtick(match: re.Match[str]) -> str:
            nonlocal counter
            col_name: str = match.group(1)
            token: str = f"{self.__placeholder_prefix}{counter}__"
            self._col_lookup[token] = col_name
            counter += 1
            return token

        processed: str = re.sub(r"`([^`]+)`", replace_backtick, query)
        processed = re.sub(r"\[([^\]]+)\]", replace_backtick, processed)

        for col in sorted(self._valid_columns, key=len, reverse=True):
            if not col.isidentifier() and col in processed:
                token = f"{self.__placeholder_prefix}{counter}__"
                self._col_lookup[token] = col
                counter += 1
                processed = processed.replace(col, token)

        processed = re.sub(r"(?<![&|])\s*&\s*(?![&|])", " and ", processed)
        processed = re.sub(r"(?<![&|])\s*\|\s*(?![&|])", " or ", processed)
        return processed

    def _extract_flat_rules(self, node: ast.AST, source_text: str) -> list[ParsedFilterRule]:
        """Flattens top level BoolUp nodes or single comparisons into a rule list"""
        if isinstance(node, ast.BoolOp):
            return self._parse_bool_op(node, source_text)

        rule: ParsedFilterRule = self._parse_single_condition(node, operator=None)
        return [rule]

    def _parse_bool_op(self, node: ast.BoolOp, source_text: str) -> list[ParsedFilterRule]:
        """Extracts sequential conds from AND/OR chains and not including nested conds"""
        if self._has_parenthesized_bool_child(node, source_text):
            raise FilterQueryParseError(
                "Nested parentheses with AND/OR are not supported by the visual row builder"
            )

        flat_pairs: list[tuple[str | None, ast.AST]] = []
        self._flatten_bool_tree(node, inherited_op=None, out_pairs=flat_pairs)

        rules: list[ParsedFilterRule] = []
        for index, (logic_op, child_node) in enumerate(flat_pairs):
            effective_op: str | None = None if index == 0 else (logic_op or FilterLogic.AND.value)
            rules.append(self._parse_single_condition(child_node, operator=effective_op))
        return rules

    def _flatten_bool_tree(
            self,
            node: ast.AST,
            inherited_op: str | None,
            out_pairs: list[tuple[str | None, ast.AST]]
    ) -> None:
        """Recursively flatten unparenthesised AND/OR chains from left to right"""
        if not isinstance(node, ast.BoolOp):
            out_pairs.append((inherited_op, node))
            return

        op_str: str = FilterLogic.AND.value if isinstance(node.op, ast.And) else FilterLogic.OR.value
        for index, value_node in enumerate(node.values):
            next_op: str | None = inherited_op if index == 0 else op_str
            self._flatten_bool_tree(value_node, next_op, out_pairs)

    @staticmethod
    def _has_parenthesized_bool_child(node: ast.BoolOp, source_text: str) -> bool:
        """Check if a child has BoolOp was wrapped in ()"""
        for value_node in node.values:
            if isinstance(value_node, ast.BoolOp):
                segment: str | None = ast.get_source_segment(source_text, value_node)
                if segment:
                    start_idx: int = source_text.find(segment)
                    if start_idx > 0 and source_text[:start_idx].rstrip().endswith("("):
                        return True
        return False

    def _parse_single_condition(self, node: ast.AST, operator: str | None) -> ParsedFilterRule:
        """Convert a single AST comparison call node into a ParsedFilterRule"""
        if isinstance(node, ast.Call):
            return self._parse_method_call(node, operator)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.Invert)):
            return self._parse_negated_call(node.operand, operator)

        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
            raise FilterQueryParseError(
                "Each condition must be a single comparison (e.g. Column > 20"
            )

        left_node: ast.AST = node.left
        op_node: ast.cmpop = node.ops[0]
        right_node: ast.AST = node.comparators[0]

        if isinstance(op_node, ast.In) and isinstance(left_node, ast.Constant) and isinstance(left_node.value, str):
            col_name: str = self._resolve_column_name(right_node)
            return ParsedFilterRule(operator, col_name, FilterCondition.CONTAINS.value, left_node.value)

        col_name = self._resolve_column_name(left_node)
        condition, value = self._resolve_operator_and_value(op_node, right_node)
        return ParsedFilterRule(operator, col_name, condition, value)

    def _parse_method_call(self, node: ast.Call, operator: str | None) -> ParsedFilterRule:
        """Support for pandas method expressions such as col.isin() and col.isna()"""
        if not isinstance(node.func, ast.Attribute):
            raise FilterQueryParseError("Unsupported function call in filter query")

        method_name: str = node.func.attr.lower()
        target_receiver: ast.AST = node.func.value

        if isinstance(target_receiver, ast.Attribute) and target_receiver.attr == "str":
            col_name: str = self._resolve_column_name(target_receiver.value)
            if method_name == "contains" and node.args:
                val: FilterScalar = self._extract_literal(node.args[0])
                return ParsedFilterRule(operator, col_name, FilterCondition.CONTAINS.value, str(val))
            raise FilterQueryParseError(f"Unsupported string method: .str.{method_name}()")

        col_name = self._resolve_column_name(target_receiver)
        if method_name in ("insa", "isnull"):
            return ParsedFilterRule(operator, col_name, FilterCondition.IS_NULL.value, None)
        if method_name in ("notna", "notnull"):
            return ParsedFilterRule(operator, col_name, FilterCondition.IS_NOT_NULL.value, None)
        if method_name == "isin" and node.args:
            list_str: str = self._extract_sequence_as_csv(node.args[0])
            return ParsedFilterRule(operator, col_name, FilterCondition.IN.value, list_str)

        raise FilterQueryParseError(f"Unsupported method '{method_name}' on column '{col_name}'")

    def _parse_negated_call(self, operand: ast.AST, operator: str | None) -> ParsedFilterRule:
        """Support negated null checks"""
        if isinstance(operand, ast.Call):
            inner_rule: ParsedFilterRule = self._parse_method_call(operand, operator)
            if inner_rule.condition == FilterCondition.IS_NULL.value:
                return ParsedFilterRule(
                    operator, inner_rule.column, FilterCondition.IS_NOT_NULL.value, None
                )
            if inner_rule.condition == FilterCondition.IS_NOT_NULL.value:
                return ParsedFilterRule(
                    operator, inner_rule.column, FilterCondition.IS_NULL.value, None
                )
        raise FilterQueryParseError("Negation ('not' / '~') only supported for null checks")

    def _resolve_column_name(self, node: ast.AST) -> str:
        """Reolsve the AST_Name node to validated column name in the DF."""
        if not isinstance(node, ast.Name):
            raise FilterQueryParseError("Left side of condition must be a column name")

        raw_name: str = self._col_lookup.get(node.id, node.id)
        if not self._valid_columns:
            return raw_name

        if raw_name in self._valid_columns:
            return raw_name

        for col in self._valid_columns:
            if col.lower() == raw_name.lower():
                return col

        raise FilterQueryParseError(f"Column '{raw_name}' does not exist the dataset")

    def _resolve_operator_and_value(
            self,
            op_node: ast.cmpop,
            right_node: ast.AST
    ) -> tuple[str, FilterScalar]:
        """Map an AST_compararer operand to rH operand to internal condition applied"""
        if self._is_null_literal(right_node):
            if isinstance(op_node, (ast.Is, ast.Eq)):
                return FilterCondition.IS_NULL.value, None
            if isinstance(op_node, (ast.IsNot, ast.NotEq)):
                return FilterCondition.IS_NOT_NULL.value, None
            raise FilterQueryParseError("Null values only support 'is', 'is not', '==' or '!='")

        if isinstance(op_node, ast.In):
            return FilterCondition.IN.value, self._extract_sequence_as_csv(right_node)

        op_map: dict[type[ast.cmpop], str] = {
            ast.Eq   : FilterCondition.EQUALS.value,
            ast.NotEq: FilterCondition.NOT_EQUALS.value,
            ast.Gt   : FilterCondition.GREATER_THAN.value,
            ast.Lt   : FilterCondition.LESS_THAN.value,
            ast.GtE  : FilterCondition.GREATER_EQUAL.value,
            ast.LtE  : FilterCondition.LESS_EQUAL.value,
        }
        condition: str | None = op_map.get(type(op_node))
        if condition is None:
            raise FilterQueryParseError(f"Unsupported operator: {type(op_node).__name__}")

        return condition, self._extract_literal(right_node)

    @staticmethod
    def _is_null_literal(node: ast.AST) -> bool:
        """Determine if an AST node represents NONE_or NAN"""
        if isinstance(node, ast.Constant) and node.value is None:
            return True
        if isinstance(node, ast.Name) and node.id.lower() in ("nan", "null", "none"):
            return True
        return False

    def _extract_sequence_as_csv(self, node: ast.AST) -> str:
        """Convert an AST into a CSV string"""
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if not node.elts:
                raise FilterQueryParseError("The 'in' list cannot be empty")
            items: list[str] = [str(self._extract_literal(elt)) for elt in node.elts]
            return ", ".join(items)

        single_val: FilterScalar = self._extract_literal(node)
        return str(single_val)

    def _extract_literal(self, node: ast.AST) -> FilterScalar:
        """Extract numerical, string, bools literals from AST nodes"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool)):
                return str(node.value) if isinstance(node.value, bool) else node.value

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            operand_val: FilterScalar = self._extract_literal(node.operand)
            if isinstance(operand_val, (int, float)):
                return -operand_val if isinstance(node.op, ast.USub) else operand_val

        if isinstance(node, ast.Name):
            resolved: str = self._col_lookup.get(node.id, node.id)
            return resolved

        raise FilterQueryParseError("Righ-hand side of comparison must be a literal value")
