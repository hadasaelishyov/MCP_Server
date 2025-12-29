"""
Core Tools - Pytest Generator MCP Server

AI-powered test generation for Python code.
Tools: analyze_code, generate_tests, run_tests, fix_code

Usage:
    from src.tools.core import TOOLS, HANDLERS
    
    # Get all tool definitions
    for tool in TOOLS:
        print(tool.name)
    
    # Get handler for a tool
    handler = HANDLERS.get("analyze_code")
    result = await handler({"code": "def add(a, b): return a + b"})
"""

__version__ = "0.1.0"

# Tool definitions and handlers
from .analyze_code import (
    TOOL_DEFINITION as ANALYZE_CODE_TOOL,
    handle as handle_analyze_code,
)

from .generate_tests import (
    TOOL_DEFINITION as GENERATE_TESTS_TOOL,
    handle as handle_generate_tests,
)

from .run_tests import (
    TOOL_DEFINITION as RUN_TESTS_TOOL,
    handle as handle_run_tests,
)

from .fix_code import (
    TOOL_DEFINITION as FIX_CODE_TOOL,
    handle as handle_fix_code,
)

# Business logic modules (for direct access if needed)
from .analyzer import analyze_code, AnalysisResult
from .generators import generate_tests, GeneratedTest
from .runner import run_tests, RunResult
from .fixer import fix_code, FixResult


# All Core tool definitions
TOOLS = [
    ANALYZE_CODE_TOOL,
    GENERATE_TESTS_TOOL,
    RUN_TESTS_TOOL,
    FIX_CODE_TOOL,
]

# Tool name to handler mapping
HANDLERS = {
    "analyze_code": handle_analyze_code,
    "generate_tests": handle_generate_tests,
    "run_tests": handle_run_tests,
    "fix_code": handle_fix_code,
}


__all__ = [
    # Version
    "__version__",
    # Tool definitions list
    "TOOLS",
    "ANALYZE_CODE_TOOL",
    "GENERATE_TESTS_TOOL",
    "RUN_TESTS_TOOL",
    "FIX_CODE_TOOL",
    # Handlers
    "HANDLERS",
    "handle_analyze_code",
    "handle_generate_tests",
    "handle_run_tests",
    "handle_fix_code",
    # Business logic (backward compatibility)
    "analyze_code",
    "AnalysisResult",
    "generate_tests",
    "GeneratedTest",
    "run_tests",
    "RunResult",
    "fix_code",
    "FixResult",
]
