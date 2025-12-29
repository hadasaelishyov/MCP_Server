"""
Complexity Analyzer - Calculate cyclomatic complexity of functions.

Cyclomatic Complexity = Number of decision points + 1

Decision points:
- if, elif
- for, while
- try/except
- and, or (boolean operators)
- comprehensions with conditions
"""

import ast
from dataclasses import dataclass, field


@dataclass
class FunctionComplexity:
    """Complexity info for a single function."""
    name: str
    complexity: int
    line_number: int
    
    @property
    def level(self) -> str:
        """Get complexity level."""
        if self.complexity <= 5:
            return "simple"
        elif self.complexity <= 10:
            return "moderate"
        elif self.complexity <= 15:
            return "complex"
        else:
            return "very_complex"


@dataclass
class ComplexityResult:
    """Result of complexity analysis."""
    average_complexity: float
    max_complexity: int
    functions: list[FunctionComplexity]
    warnings: list[str] = field(default_factory=list)


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to count complexity."""
    
    def __init__(self):
        self.complexity = 1  # Base complexity
    
    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        # 'and' / 'or' add complexity
        self.complexity += len(node.values) - 1
        self.generic_visit(node)
    
    def visit_IfExp(self, node):
        # Ternary: x if condition else y
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_ListComp(self, node):
        # List comprehension with conditions
        for generator in node.generators:
            self.complexity += len(generator.ifs)
        self.generic_visit(node)
    
    def visit_DictComp(self, node):
        for generator in node.generators:
            self.complexity += len(generator.ifs)
        self.generic_visit(node)
    
    def visit_SetComp(self, node):
        for generator in node.generators:
            self.complexity += len(generator.ifs)
        self.generic_visit(node)


def analyze_complexity(code: str, max_complexity: int = 10) -> ComplexityResult:
    """
    Analyze cyclomatic complexity of Python code.
    
    Args:
        code: Python source code as string
        max_complexity: Threshold for warnings (default: 10)
        
    Returns:
        ComplexityResult with complexity details
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ComplexityResult(
            average_complexity=0,
            max_complexity=0,
            functions=[],
            warnings=["Cannot analyze complexity: syntax error in code"]
        )
    
    functions = []
    warnings = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Calculate complexity for this function
            visitor = ComplexityVisitor()
            visitor.visit(node)
            
            func_complexity = FunctionComplexity(
                name=node.name,
                complexity=visitor.complexity,
                line_number=node.lineno
            )
            functions.append(func_complexity)
            
            # Add warning if too complex
            if visitor.complexity > max_complexity:
                warnings.append(
                    f"Function '{node.name}' has high complexity ({visitor.complexity}). "
                    f"Consider breaking it into smaller functions."
                )
    
    # Calculate statistics
    if functions:
        avg = sum(f.complexity for f in functions) / len(functions)
        max_val = max(f.complexity for f in functions)
    else:
        avg = 0
        max_val = 0
    
    return ComplexityResult(
        average_complexity=round(avg, 1),
        max_complexity=max_val,
        functions=functions,
        warnings=warnings
    )