"""MCP handler for fix_code (delegates to FixingService)."""

from __future__ import annotations

from mcp.types import TextContent, Tool

from ...services import FixingService, ServiceResult

# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
    name="fix_code",
    description=(
        "Automatically fix bugs in Python code based on failing tests. "
        "Analyzes test failures, identifies bugs, generates minimal fixes using AI, "
        "and verifies the fix by re-running tests."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "source_code": {
                "type": "string",
                "description": "The Python source code to fix (contains bugs)"
            },
            "test_code": {
                "type": "string",
                "description": "The pytest test code that tests the source"
            },
            "test_output": {
                "type": "string",
                "description": "Raw pytest output (optional - will run tests if not provided)"
            },
            "verify": {
                "type": "boolean",
                "description": "Whether to verify the fix by re-running tests (default: true)"
            }
        },
        "required": ["source_code", "test_code"]
    }
)


# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """Fix code using provided tests (and optional output) and return the formatted result."""
    
    service = FixingService()

    result =await service.fix(
        source_code=arguments.get("source_code", ""),
        test_code=arguments.get("test_code", ""),
        test_output=arguments.get("test_output"),
        verify=arguments.get("verify", True)
    )

    if not result.success:
        return _error_response(result)

    fix_result = result.data

    # Format response
    return [TextContent(
        type="text",
        text=format_fix_result(fix_result)
    )]


# =============================================================================
# Response Formatting
# =============================================================================

def format_fix_result(fix_result) -> str:
    """Format fix result as readable text."""
    lines = [
        "🔧 CODE FIX RESULTS",
        "=" * 50,
        "",
    ]

    if not fix_result.success:
        lines.append(f"❌ Fix failed: {fix_result.error}")
        return "\n".join(lines)

    lines.extend([
        "✅ Fix generated successfully!",
        f"Confidence: {fix_result.confidence}",
        ""
    ])

    # Bugs found
    if fix_result.bugs_found:
        lines.append(f"🐛 Bugs Found ({len(fix_result.bugs_found)}):")
        for i, bug in enumerate(fix_result.bugs_found, 1):
            loc = f"[Line {bug.line_number}] " if bug.line_number else ""
            lines.append(f"  {i}. {loc}{bug.description}")
        lines.append("")

    # Fixes applied
    if fix_result.fixes_applied:
        lines.append(f"🔨 Fixes Applied ({len(fix_result.fixes_applied)}):")
        for i, fix in enumerate(fix_result.fixes_applied, 1):
            loc = f"[Line {fix.line_number}] " if fix.line_number else ""
            lines.append(f"  {i}. {loc}{fix.description}")
            lines.append(f"     Reason: {fix.reason}")
        lines.append("")

    # Verification
    if fix_result.verification:
        v = fix_result.verification
        lines.append("🧪 Verification:")
        if v.passed:
            lines.append(f"  ✅ All tests pass! ({v.tests_passed}/{v.tests_total})")
        else:
            lines.append(f"  ⚠️ {v.tests_passed}/{v.tests_total} tests pass")
            if v.error_message:
                lines.append(f"  Error: {v.error_message}")
        lines.append("")

    # Fixed code
    lines.extend([
        "=" * 50,
        "FIXED CODE:",
        "=" * 50,
        "",
        fix_result.fixed_code or ""
    ])

    return "\n".join(lines)


# =============================================================================
# Helpers
# =============================================================================

def _error_response(result: ServiceResult) -> list[TextContent]:
    """Create error response from failed ServiceResult."""
    return [TextContent(type="text", text=f"Error: {result.error.message}")]
