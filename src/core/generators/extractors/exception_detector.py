"""
Exception Detector - Find raise statements in function AST.

Detects what exceptions a function can raise so we can test them.
"""

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


def detect_exceptions(code: str, function_name: str) -> list[DetectedException]:
    """
    Detect exceptions raised by a function.
    
    Args:
        code: Complete source code
        function_name: Name of function to analyze
        
    Returns:
        List of DetectedException objects
    """
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
    """Extract all raise statements from a function."""
    exceptions = []

    for node in ast.walk(func_node):
        if isinstance(node, ast.Raise):
            exc = _parse_raise(node)
            if exc:
                exceptions.append(exc)

    return exceptions


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
    """
    Escape a message string for use in pytest.raises(match=...).
    
    Uses re.escape() to properly escape ALL regex special characters.
    Truncates long messages to avoid overly specific matching.
    
    Args:
        message: The exception message to escape
        max_length: Maximum length before truncation (default: 40)
        
    Returns:
        Escaped string safe for regex matching
    
    Examples:
        "Expected (x, y)" -> "Expected\\ \\(x,\\ y\\)"
        "Price must be >= 0" -> "Price\\ must\\ be\\ \\>=\\ 0"
        "Use $100" -> "Use\\ \\$100"
    """
    # Escape all regex special characters
    escaped = re.escape(message)

    # Truncate if too long (keeps the match focused on key part)
    if len(escaped) > max_length:
        escaped = escaped[:max_length]

    return escaped


def format_match_string(message: str) -> str:
    """
    Format an exception message as a pytest match parameter.
    
    Handles:
    - Regex escaping for special characters
    - Quotes inside the message
    - Long messages (truncation)
    - Empty messages
    
    Args:
        message: The exception message
        
    Returns:
        Formatted match string like 'match=r"..."' or 'match=r"..."'
    """
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
    """
    Generate test code for an exception.
    
    Args:
        func_name: Function name
        exception: Detected exception info
        param_values: Pre-formatted parameter string like "0.0, 0.0"
        
    Returns:
        List of test code lines
    """
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
        f"    {func_call}  # TODO: adjust inputs to trigger exception"
    ]


def get_safe_trigger_hint(exception: DetectedException) -> str | None:
    """
    Try to suggest inputs that might trigger the exception.
    
    Based on common patterns in exception messages.
    This is a hint, not a guarantee.
    
    Args:
        exception: The detected exception
        
    Returns:
        Hint string or None if no pattern matched
    """
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
