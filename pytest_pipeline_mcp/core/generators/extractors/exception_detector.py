"""Detect raised exceptions in a function AST and generate pytest.raises snippets."""

import ast
import re
from dataclasses import dataclass


@dataclass
class DetectedException:
    """An exception that can be raised by a function."""
    exception_type: str     # "ValueError"
    condition: str | None   # "if x < 0" (simplified)
    message: str | None     # "x must be positive"
    line_number: int = 0    # Line where exception is raised
    condition_ast: ast.expr | None = None  

class _RaiseCollector(ast.NodeVisitor):
    """AST visitor that collects raise statements with their surrounding conditions.
    
    Algorithm:
    ---------
    Uses a stack-based approach to track nested if/elif/else conditions:
    
    1. When entering an `if` block, push its test condition onto the stack
    2. When entering `elif`, push NOT(previous_test) AND elif_test
    3. When entering `else`, push NOT(previous_test)
    4. When exiting any block, pop the condition from the stack
    5. When a `raise` is found, combine all stacked conditions with AND
    
    Example:
        if x < 0:           # stack: [x < 0]
            if y == 0:      # stack: [x < 0, y == 0]
                raise ...   # condition = (x < 0) AND (y == 0)
    
    This correctly captures the full condition path leading to each exception.
    """
    def __init__(self) -> None:
        # Stack of conditions leading to current position in AST
        self._conds: list[ast.expr] = []
        # Collected exceptions with their trigger conditions
        self.exceptions: list[DetectedException] = []

    def _current_condition_ast(self) -> ast.expr | None:
        if not self._conds:
            return None
        if len(self._conds) == 1:
            return self._conds[0]
        return ast.BoolOp(op=ast.And(), values=list(self._conds))  # combine with AND

    def visit_Raise(self, node: ast.Raise) -> None:
        exc = _parse_raise(node)
        if exc:
            cond_ast = self._current_condition_ast()
            exc.condition_ast = cond_ast
            exc.condition = ast.unparse(cond_ast) if cond_ast else None  # readable condition
            self.exceptions.append(exc)

    def visit_If(self, node: ast.If) -> None:
        # handle "if <test>: ..."
        self._conds.append(node.test)
        for stmt in node.body:
            self.visit(stmt)
        self._conds.pop()

        # handle elif/else using NOT(test)
        not_test = ast.UnaryOp(op=ast.Not(), operand=node.test)

        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            # elif
            self._conds.append(not_test)
            self.visit(node.orelse[0])
            self._conds.pop()
        elif node.orelse:
            # else
            self._conds.append(not_test)
            for stmt in node.orelse:
                self.visit(stmt)
            self._conds.pop()

def detect_exceptions(code: str, function_name: str) -> list[DetectedException]:
    """Detect exceptions raised by the given function in the provided source."""

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    exceptions = []

    # Find the function
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                exceptions = _extract_raises(node)
                break

    return exceptions


def _extract_raises(func_node: ast.FunctionDef) -> list[DetectedException]:
    """Extract raises with surrounding if/else conditions."""
    collector = _RaiseCollector()
    collector.visit(func_node)
    return collector.exceptions


def _parse_raise(node: ast.Raise) -> DetectedException | None:
    """Parse a raise statement into DetectedException."""
    if node.exc is None:
        return None  # bare 'raise'

    exception_type = None
    message = None

    # Handle: raise ValueError("message")
    if isinstance(node.exc, ast.Call):
        if isinstance(node.exc.func, ast.Name):
            exception_type = node.exc.func.id
        elif isinstance(node.exc.func, ast.Attribute):
            exception_type = node.exc.func.attr

        # Try to get message
        if node.exc.args:
            first_arg = node.exc.args[0]
            if isinstance(first_arg, ast.Constant):
                message = str(first_arg.value)

    # Handle: raise ValueError
    elif isinstance(node.exc, ast.Name):
        exception_type = node.exc.id

    if exception_type:
        return DetectedException(
            exception_type=exception_type,
            condition=None,
            message=message,
            line_number=node.lineno
        )

    return None


def escape_for_regex(message: str, max_length: int = 40) -> str:
    """Escape an exception message for use in pytest.raises(match=...) (optionally truncating)."""

    # Escape all regex special characters
    escaped = re.escape(message)

    # Truncate if too long (keeps the match focused on key part)
    if len(escaped) > max_length:
        escaped = escaped[:max_length]

    return escaped


def format_match_string(message: str) -> str:
    """Format a safe pytest.raises(match=...) argument for the given exception message."""

    if not message:
        return ""

    # Escape for regex
    escaped = escape_for_regex(message)

    # Choose quote style based on content
    # If message contains double quotes, use single quotes for the string
    if '"' in escaped and "'" not in escaped:
        return f"match=r'{escaped}'"
    elif "'" in escaped and '"' not in escaped:
        return f'match=r"{escaped}"'
    elif '"' in escaped and "'" in escaped:
        # Both quotes present - escape double quotes and use double quote string
        escaped = escaped.replace('"', r'\"')
        return f'match=r"{escaped}"'
    else:
        # No quotes - use double quotes (conventional)
        return f'match=r"{escaped}"'


def generate_exception_test(
    func_name: str,
    exception: DetectedException,
    param_values: str = ""
) -> list[str]:
    """Generate pytest.raises(...) lines for a detected exception."""

    # Build function call with params
    if param_values:
        func_call = f"{func_name}({param_values})"
    else:
        func_call = f"{func_name}()"

    # Build the raises context manager
    if exception.message:
        match_str = format_match_string(exception.message)
        raises_line = f"with pytest.raises({exception.exception_type}, {match_str}):"
    else:
        raises_line = f"with pytest.raises({exception.exception_type}):"

    return [
        raises_line,
        f"    {func_call}  # triggers the exception condition"
    ]


def get_safe_trigger_hint(exception: DetectedException) -> str | None:
    """Heuristic hint for inputs that might trigger the detected exception."""
    if not exception.message:
        return None

    msg = exception.message.lower()
    
    # Common patterns
    if "empty" in msg:
        return "Try passing empty string or empty list"
    if "negative" in msg or "< 0" in msg or "<0" in msg:
        return "Try passing negative value"
    if "zero" in msg or "= 0" in msg or "== 0" in msg:
        return "Try passing zero"
    if "none" in msg or "null" in msg:
        return "Try passing None"
    if "positive" in msg or "> 0" in msg:
        return "Try passing zero or negative value"
    if "between" in msg or "range" in msg:
        return "Try passing value outside the valid range"

    return None

def infer_trigger_overrides(
    condition_ast: ast.expr | None,
    params: list[tuple[str, str | None]],
) -> dict[str, str]:
    """
    Return overrides that satisfy the condition.
    
    Heuristic overrides: try to satisfy *simple* raise conditions (e.g., x == 0, x < 0, x is None, not x).
    We intentionally avoid complex expressions to keep generated tests safe and predictable.
    """
    if condition_ast is None:
        return {}

    type_by = {n: t for n, t in params}

    def neg_value(name: str) -> str | None:
        t = (type_by.get(name) or "").replace("typing.", "")
        if "float" in t:
            return "-1.0"
        if "int" in t:
            return "-1"
        return None

    def zero_value(name: str) -> str:
        t = (type_by.get(name) or "").replace("typing.", "")
        return "0.0" if "float" in t else "0"

    # handle simple comparisons like b == 0, x < 0, y is None, not s, len(items) == 0
    if isinstance(condition_ast, ast.Compare) and len(condition_ast.ops) == 1 and len(condition_ast.comparators) == 1:
        left = condition_ast.left
        op = condition_ast.ops[0]
        right = condition_ast.comparators[0]

        if isinstance(left, ast.Name):
            name = left.id

            if isinstance(op, ast.Eq) and isinstance(right, ast.Constant) and right.value == 0:
                return {name: zero_value(name)}
            if isinstance(op, (ast.Lt, ast.LtE)) and isinstance(right, ast.Constant) and right.value == 0:
                nv = neg_value(name)
                return {name: nv} if nv else {}
            if isinstance(op, ast.Is) and isinstance(right, ast.Constant) and right.value is None:
                return {name: "None"}

    if isinstance(condition_ast, ast.UnaryOp) and isinstance(condition_ast.op, ast.Not):
        # not x  -> set x to empty/False-ish
        if isinstance(condition_ast.operand, ast.Name):
            name = condition_ast.operand.id
            return {name: '""'}  # default falsy for strings; you can expand by type

    # if we can't infer safely, return empty dict
    return {}
