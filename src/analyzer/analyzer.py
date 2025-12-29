"""
Code Analyzer - Main analysis engine that combines parsing and validation.
"""

from .parser import parse_code, extract_functions, extract_classes
from .models import AnalysisResult, FunctionInfo
from .syntax_validator import validate_syntax
from .type_hint_checker import check_type_hints


def analyze_code(code: str) -> AnalysisResult:
    """
    Analyze Python code completely.
    
    This is the main entry point that:
    1. Validates syntax
    2. Parses code structure
    3. Extracts functions and classes
    4. Checks type hints
    5. Calculates complexity
    6. Generates warnings
    
    Args:
        code: Python source code as string
        
    Returns:
        AnalysisResult with all analysis data
    """
    # Step 1: Validate syntax
    syntax_result = validate_syntax(code)
    
    if not syntax_result.is_valid:
        return AnalysisResult(
            valid=False,
            error=f"Syntax error at line {syntax_result.error_line}: {syntax_result.error_message}"
        )
    
    # Step 2: Parse code
    tree = parse_code(code)
    if tree is None:
        return AnalysisResult(
            valid=False,
            error="Failed to parse code"
        )
    
    # Step 3: Extract functions and classes
    functions = extract_functions(tree)
    classes = extract_classes(tree)
    
    # Step 4: Collect all functions (including methods) for statistics
    all_functions = list(functions)
    for cls in classes:
        all_functions.extend(cls.methods)
    
    # Step 5: Generate warnings
    warnings = _generate_warnings(all_functions, code)
    
    # Step 6: Calculate statistics
    stats = _calculate_statistics(all_functions)
    
    return AnalysisResult(
        valid=True,
        functions=functions,
        classes=classes,
        warnings=warnings,
        total_functions=stats["total_functions"],
        total_classes=len(classes),
        average_complexity=stats["average_complexity"],
        type_hint_coverage=stats["type_hint_coverage"]
    )


def _generate_warnings(functions: list[FunctionInfo], code: str) -> list[str]:
    """Generate warnings based on analysis."""
    warnings = []
    
    # Type hint warnings
    type_result = check_type_hints(code)
    warnings.extend(type_result.warnings)
    
    # Complexity warnings
    for func in functions:
        if func.complexity > 10:
            warnings.append(
                f"Function '{func.name}' has high complexity ({func.complexity}). "
                f"Consider breaking it into smaller functions."
            )
        elif func.complexity > 7:
            warnings.append(
                f"Function '{func.name}' has moderate complexity ({func.complexity})."
            )
    
    # Missing docstring warnings
    for func in functions:
        if not func.docstring and not func.name.startswith('_'):
            warnings.append(
                f"Function '{func.name}' has no docstring."
            )
    
    return warnings


def _calculate_statistics(functions: list[FunctionInfo]) -> dict:
    """Calculate statistics from analyzed functions."""
    if not functions:
        return {
            "total_functions": 0,
            "average_complexity": 0.0,
            "type_hint_coverage": 100.0
        }
    
    total = len(functions)
    
    # Average complexity
    total_complexity = sum(f.complexity for f in functions)
    avg_complexity = round(total_complexity / total, 1)
    
    # Type hint coverage
    typed_count = sum(1 for f in functions if f.is_fully_typed)
    type_coverage = round((typed_count / total) * 100, 1)
    
    return {
        "total_functions": total,
        "average_complexity": avg_complexity,
        "type_hint_coverage": type_coverage
    }


def analyze_file(file_path: str) -> AnalysisResult:
    """
    Analyze a Python file.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        AnalysisResult with all analysis data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return analyze_code(code)
    except FileNotFoundError:
        return AnalysisResult(
            valid=False,
            error=f"File not found: {file_path}"
        )
    except PermissionError:
        return AnalysisResult(
            valid=False,
            error=f"Permission denied: {file_path}"
        )
    except Exception as e:
        return AnalysisResult(
            valid=False,
            error=f"Error reading file: {str(e)}"
        )