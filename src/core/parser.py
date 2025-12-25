"""
Code Parser - Parse Python code using AST and extract structure.
"""

import ast
from .models import ParameterInfo, FunctionInfo, ClassInfo


def parse_code(code: str) -> ast.Module | None:
    """
    Parse Python code into AST.
    
    Args:
        code: Python source code
        
    Returns:
        AST module or None if syntax error
    """
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


def extract_functions(tree: ast.Module) -> list[FunctionInfo]:
    """
    Extract all top-level functions from AST.
    
    Args:
        tree: Parsed AST module
        
    Returns:
        List of FunctionInfo objects
    """
    functions = []
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = _parse_function(node, is_method=False)
            functions.append(func_info)
    
    return functions


def extract_classes(tree: ast.Module) -> list[ClassInfo]:
    """
    Extract all classes from AST.
    
    Args:
        tree: Parsed AST module
        
    Returns:
        List of ClassInfo objects
    """
    classes = []
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_info = _parse_class(node)
            classes.append(class_info)
    
    return classes


def _parse_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool = False
) -> FunctionInfo:
    """Parse a function node into FunctionInfo."""
    
    # Extract parameters
    parameters = _parse_parameters(node.args)
    
    # Extract return type
    return_type = None
    if node.returns:
        return_type = _get_annotation_string(node.returns)
    
    # Extract docstring
    docstring = ast.get_docstring(node)
    
    # Check decorators for static/classmethod
    is_static = False
    is_classmethod = False
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id == 'staticmethod':
                is_static = True
            elif decorator.id == 'classmethod':
                is_classmethod = True
    
    # Calculate complexity
    complexity = _calculate_complexity(node)
    
    return FunctionInfo(
        name=node.name,
        parameters=parameters,
        return_type=return_type,
        docstring=docstring,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        is_method=is_method,
        is_static=is_static,
        is_classmethod=is_classmethod,
        line_number=node.lineno,
        complexity=complexity
    )


def _parse_class(node: ast.ClassDef) -> ClassInfo:
    """Parse a class node into ClassInfo."""
    
    # Extract methods
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_info = _parse_function(item, is_method=True)
            methods.append(method_info)
    
    # Extract docstring
    docstring = ast.get_docstring(node)
    
    # Extract base classes
    base_classes = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            base_classes.append(base.id)
        elif isinstance(base, ast.Attribute):
            base_classes.append(_get_attribute_string(base))
    
    return ClassInfo(
        name=node.name,
        methods=methods,
        docstring=docstring,
        line_number=node.lineno,
        base_classes=base_classes
    )


def _parse_parameters(args: ast.arguments) -> list[ParameterInfo]:
    """Parse function arguments into ParameterInfo list."""
    parameters = []
    
    # Calculate defaults offset
    # defaults are aligned to the END of args
    num_args = len(args.args)
    num_defaults = len(args.defaults)
    defaults_offset = num_args - num_defaults
    
    for i, arg in enumerate(args.args):
        # Get type hint
        type_hint = None
        if arg.annotation:
            type_hint = _get_annotation_string(arg.annotation)
        
        # Get default value
        default_value = None
        has_default = False
        default_index = i - defaults_offset
        if default_index >= 0 and default_index < len(args.defaults):
            has_default = True
            default_value = _get_default_string(args.defaults[default_index])
        
        parameters.append(ParameterInfo(
            name=arg.arg,
            type_hint=type_hint,
            default_value=default_value,
            has_default=has_default
        ))
    
    # Handle *args
    if args.vararg:
        type_hint = None
        if args.vararg.annotation:
            type_hint = _get_annotation_string(args.vararg.annotation)
        parameters.append(ParameterInfo(
            name=f"*{args.vararg.arg}",
            type_hint=type_hint
        ))
    
    # Handle **kwargs
    if args.kwarg:
        type_hint = None
        if args.kwarg.annotation:
            type_hint = _get_annotation_string(args.kwarg.annotation)
        parameters.append(ParameterInfo(
            name=f"**{args.kwarg.arg}",
            type_hint=type_hint
        ))
    
    return parameters


def _get_annotation_string(node: ast.expr) -> str:
    """Convert annotation AST node to string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Subscript):
        # Handle generics like list[int], Optional[str]
        base = _get_annotation_string(node.value)
        slice_val = _get_annotation_string(node.slice)
        return f"{base}[{slice_val}]"
    elif isinstance(node, ast.Attribute):
        return _get_attribute_string(node)
    elif isinstance(node, ast.Tuple):
        # Handle tuple types like tuple[int, str]
        elements = [_get_annotation_string(el) for el in node.elts]
        return ", ".join(elements)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Handle union types like int | None
        left = _get_annotation_string(node.left)
        right = _get_annotation_string(node.right)
        return f"{left} | {right}"
    else:
        return "Any"


def _get_attribute_string(node: ast.Attribute) -> str:
    """Convert attribute access to string (e.g., typing.Optional)."""
    if isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    elif isinstance(node.value, ast.Attribute):
        return f"{_get_attribute_string(node.value)}.{node.attr}"
    return node.attr


def _get_default_string(node: ast.expr) -> str:
    """Convert default value AST node to string."""
    if isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.List):
        return "[]"
    elif isinstance(node, ast.Dict):
        return "{}"
    elif isinstance(node, ast.Tuple):
        return "()"
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return f"{node.func.id}()"
        return "..."
    else:
        return "..."


def _calculate_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate cyclomatic complexity for a function."""
    complexity = 1  # Base complexity
    
    for child in ast.walk(node):
        # Decision points
        if isinstance(child, ast.If):
            complexity += 1
        elif isinstance(child, ast.For):
            complexity += 1
        elif isinstance(child, ast.While):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.With):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # 'and' / 'or' operators
            complexity += len(child.values) - 1
        elif isinstance(child, ast.IfExp):
            # Ternary expression
            complexity += 1
        elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            # Comprehensions with conditions
            for generator in child.generators:
                complexity += len(generator.ifs)
    
    return complexity