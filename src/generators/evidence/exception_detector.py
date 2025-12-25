"""
Exception Detector - Find raise statements in function AST.

Detects what exceptions a function can raise so we can test them.
"""

import ast
from dataclasses import dataclass


@dataclass
class DetectedException:
    """An exception that can be raised by a function."""
    exception_type: str     # "ValueError"
    condition: str | None   # "if x < 0" (simplified)
    message: str | None     # "x must be positive"


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
            message=message
        )
    
    return None


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
    if exception.message and len(exception.message) <= 20:
        raises_line = f'with pytest.raises({exception.exception_type}, match="{exception.message}"):'
    elif exception.message:
        raises_line = f'with pytest.raises({exception.exception_type}, match=r".*{exception.message[:20]}.*"):'
    else:
        raises_line = f"with pytest.raises({exception.exception_type}):"
    
    return [
        raises_line,
        f"    {func_call}  # May need adjustment to trigger exception"
    ]