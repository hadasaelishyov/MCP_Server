"""Registry for core MCP tool definitions and handlers."""

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
    # Tool definitions
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
]