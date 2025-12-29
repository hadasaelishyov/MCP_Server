"""
Type Hint Checker - Check if functions have type annotations.
"""

import ast
from dataclasses import dataclass, field


@dataclass
class FunctionHintInfo:
    """Type hint info for a single function."""
    name: str
    has_return_hint: bool
    params_total: int
    params_with_hints: int
    missing_hints: list[str] = field(default_factory=list)
    
    @property
    def is_fully_typed(self) -> bool:
        """Check if function has all type hints."""
        return self.has_return_hint and self.params_total == self.params_with_hints


@dataclass
class TypeHintResult:
    """Result of type hint analysis."""
    status: str  # "complete" | "partial" | "missing"
    coverage_percentage: float
    functions: list[FunctionHintInfo]
    warnings: list[str] = field(default_factory=list)


def check_type_hints(code: str) -> TypeHintResult:
    """
    Check type hint coverage in Python code.
    
    Args:
        code: Python source code as string
        
    Returns:
        TypeHintResult with coverage details
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return TypeHintResult(
            status="error",
            coverage_percentage=0,
            functions=[],
            warnings=["Cannot check type hints: syntax error in code"]
        )
    
    functions = []
    warnings = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = _analyze_function(node)
            functions.append(func_info)
            
            # Generate warnings for missing hints
            if not func_info.is_fully_typed:
                if not func_info.has_return_hint:
                    warnings.append(f"Function '{func_info.name}' missing return type hint")
                for param in func_info.missing_hints:
                    warnings.append(f"Function '{func_info.name}' missing type hint for parameter '{param}'")
    
    # Calculate overall coverage
    coverage = _calculate_coverage(functions)
    
    # Determine status
    if coverage == 100:
        status = "complete"
    elif coverage > 0:
        status = "partial"
    else:
        status = "missing"
    
    return TypeHintResult(
        status=status,
        coverage_percentage=coverage,
        functions=functions,
        warnings=warnings
    )


def _analyze_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionHintInfo:
    """Analyze type hints for a single function."""
    # Check return type hint
    has_return_hint = node.returns is not None
    
    # Analyze parameters (skip 'self' and 'cls')
    params_total = 0
    params_with_hints = 0
    missing_hints = []
    
    for arg in node.args.args:
        # Skip 'self' and 'cls'
        if arg.arg in ('self', 'cls'):
            continue
            
        params_total += 1
        if arg.annotation is not None:
            params_with_hints += 1
        else:
            missing_hints.append(arg.arg)
    
    return FunctionHintInfo(
        name=node.name,
        has_return_hint=has_return_hint,
        params_total=params_total,
        params_with_hints=params_with_hints,
        missing_hints=missing_hints
    )


def _calculate_coverage(functions: list[FunctionHintInfo]) -> float:
    """Calculate overall type hint coverage percentage."""
    if not functions:
        return 100.0  # No functions = nothing to check
    
    total_items = 0
    hinted_items = 0
    
    for func in functions:
        # Count return type
        total_items += 1
        if func.has_return_hint:
            hinted_items += 1
        
        # Count parameters
        total_items += func.params_total
        hinted_items += func.params_with_hints
    
    if total_items == 0:
        return 100.0
        
    return round((hinted_items / total_items) * 100, 1)