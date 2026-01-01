"""Data models for code analysis."""

from dataclasses import dataclass, field
from typing import Literal

# Parameter kinds matching Python's inspect module
ParameterKind = Literal[
    "positional_only",      # Before /
    "positional_or_keyword", # Normal parameters
    "var_positional",       # *args
    "keyword_only",         # After * or *args
    "var_keyword"           # **kwargs
]


@dataclass
class ParameterInfo:
    """Information about a function parameter."""
    name: str
    type_hint: str | None = None
    default_value: str | None = None
    has_default: bool = False
    kind: ParameterKind = "positional_or_keyword"


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    parameters: list[ParameterInfo]
    return_type: str | None = None
    docstring: str | None = None
    is_async: bool = False
    is_method: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    line_number: int = 0
    complexity: int = 1

    @property
    def has_type_hints(self) -> bool:
        """Check if function has any type hints."""
        if self.return_type:
            return True
        return any(p.type_hint for p in self.parameters)

    @property
    def is_fully_typed(self) -> bool:
        """Check if function has complete type hints."""
        if not self.return_type:
            return False
        for param in self.parameters:
            if param.name not in ('self', 'cls') and not param.type_hint:
                return False
        return True


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    methods: list[FunctionInfo]
    docstring: str | None = None
    line_number: int = 0
    base_classes: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete analysis result for a Python file/code."""
    valid: bool
    error: str | None = None
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Statistics
    total_functions: int = 0
    total_classes: int = 0
    average_complexity: float = 0.0
    type_hint_coverage: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "valid": self.valid,
            "error": self.error,
            "functions": [
                {
                    "name": f.name,
                    "parameters": [
                        {
                            "name": p.name,
                            "type_hint": p.type_hint,
                            "has_default": p.has_default,
                            "kind": p.kind
                        }
                        for p in f.parameters
                    ],
                    "return_type": f.return_type,
                    "docstring": f.docstring,
                    "is_async": f.is_async,
                    "complexity": f.complexity,
                    "line_number": f.line_number
                }
                for f in self.functions
            ],
            "classes": [
                {
                    "name": c.name,
                    "methods": [m.name for m in c.methods],
                    "docstring": c.docstring,
                    "line_number": c.line_number
                }
                for c in self.classes
            ],
            "warnings": self.warnings,
            "statistics": {
                "total_functions": self.total_functions,
                "total_classes": self.total_classes,
                "average_complexity": self.average_complexity,
                "type_hint_coverage": self.type_hint_coverage
            }
        }
