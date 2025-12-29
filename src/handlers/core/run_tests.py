"""
Run Tests Tool - Execute pytest tests and measure code coverage.

This tool:
1. Takes source code and test code
2. Runs in isolated temporary environment
3. Reports pass/fail results
4. Measures code coverage via pytest-cov

Uses ExecutionService for business logic.
"""

from __future__ import annotations

from mcp.types import TextContent, Tool

from ...services import ExecutionService, ServiceResult

# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
    name="run_tests",
    description=(
        "Execute pytest tests and measure code coverage. "
        "Takes source code and test code, runs in isolated environment, "
        "returns pass/fail results with coverage metrics."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "source_code": {
                "type": "string",
                "description": "The Python source code to test"
            },
            "test_code": {
                "type": "string",
                "description": "The pytest test code to execute"
            }
        },
        "required": ["source_code", "test_code"]
    }
)


# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """
    Handle run_tests tool call.
    
    Args:
        arguments: Tool arguments (source_code, test_code)
        
    Returns:
        List with single TextContent containing test results
    """
    service = ExecutionService()

    result = service.run(
        source_code=arguments.get("source_code", ""),
        test_code=arguments.get("test_code", "")
    )

    if not result.success:
        return _error_response(result)

    run_result = result.data

    # Format response
    return [TextContent(
        type="text",
        text=format_test_results(run_result)
    )]


# =============================================================================
# Response Formatting
# =============================================================================

def format_test_results(run_result) -> str:
    """Format test execution results as readable text."""
    lines = [
        "TEST EXECUTION RESULTS",
        "=" * 50,
        "",
        "✅ All tests passed!" if run_result.success else "❌ Some tests failed",
        "",
        "Summary:",
        f"  • Total:  {run_result.total}",
        f"  • Passed: {run_result.passed}",
        f"  • Failed: {run_result.failed}",
    ]

    if run_result.errors > 0:
        lines.append(f"  • Errors: {run_result.errors}")

    # Coverage
    if run_result.coverage:
        cov = run_result.coverage
        lines.extend([
            "",
            "Code Coverage:",
            f"  • Coverage: {cov.percentage:.1f}%",
            f"  • Lines covered: {cov.covered_lines}/{cov.total_lines}",
        ])
        if cov.missing_lines:
            missing = ", ".join(str(l) for l in cov.missing_lines[:10])
            if len(cov.missing_lines) > 10:
                missing += f"... (+{len(cov.missing_lines) - 10} more)"
            lines.append(f"  • Missing lines: {missing}")

    # Passed tests
    if run_result.passed_tests:
        lines.append("")
        lines.append("Passed tests:")
        for name in run_result.passed_tests:
            lines.append(f"  ✓ {name}")

    # Failed tests
    if run_result.failed_tests:
        lines.append("")
        lines.append("Failed tests:")
        for failed in run_result.failed_tests:
            lines.append(f"  ✗ {failed['name']}")
            if failed.get("error"):
                lines.append(f"    Error: {failed['error']}")

    # Error message
    if run_result.error_message:
        lines.append("")
        lines.append(f"Error: {run_result.error_message}")

    return "\n".join(lines)


# =============================================================================
# Helpers
# =============================================================================

def _error_response(result: ServiceResult) -> list[TextContent]:
    """Create error response from failed ServiceResult."""
    return [TextContent(type="text", text=f"Error: {result.error.message}")]
