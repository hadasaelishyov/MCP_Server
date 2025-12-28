"""Pytest Generator MCP Server - Generate pytest tests using static code analysis."""

__version__ = "0.1.0"

# Export fixer for convenience
from .fixer import fix_code, CodeFixer, FixResult

__all__ = [
    "__version__",
    "fix_code",
    "CodeFixer", 
    "FixResult",
]