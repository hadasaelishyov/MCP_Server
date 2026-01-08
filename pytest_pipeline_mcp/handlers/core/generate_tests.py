"""MCP handler for generate_tests (delegates to GenerationService)."""

from __future__ import annotations

from mcp.types import TextContent, Tool

from ...services import GenerationService, ServiceResult

# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
    name="generate_tests",
    description=(
        "Generate pytest test cases for Python code. "
        "Uses template-based generation with evidence-based enrichment: "
        "doctest extraction, type assertions, exception detection, "
        "boundary values, and naming heuristics. "
        "Optionally uses AI to enhance assertions with real expected values."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the Python file to generate tests for"
            },
            "code": {
                "type": "string",
                "description": "Python code content (alternative to file_path)"
            },
            "output_path": {
                "type": "string",
                "description": "Path where to save the generated test file (optional)"
            },
            "include_edge_cases": {
                "type": "boolean",
                "description": "Whether to generate edge case tests (default: true)"
            },
            "use_ai": {
                "type": "boolean",
                "description": "Whether to use AI to enhance tests (default: false)"
            }
        }
    }
)


# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """Generate pytest tests from 'code' or 'file_path' and return the result text."""
    service = GenerationService()

    result = service.generate(
        code=arguments.get("code"),
        file_path=arguments.get("file_path"),
        output_path=arguments.get("output_path"),
        include_edge_cases=arguments.get("include_edge_cases", True),
        use_ai=arguments.get("use_ai", False)
    )

    if not result.success:
        return _error_response(result)

    gen_result = result.data
    tests = gen_result.tests
    meta = gen_result.metadata

    # Format response
    return [TextContent(
        type="text",
        text=format_generation_result(tests, meta)
    )]


# =============================================================================
# Response Formatting
# =============================================================================

def format_generation_result(tests, meta) -> str:
    """Format test generation result as readable text."""
    lines = [
        f"Generated {len(tests.test_cases)} test(s) for "
        f"{meta.function_count} function(s) and {meta.class_count} class(es)",
        f"Mode: {meta.mode}",
        "",
        "Test breakdown by evidence source:",
    ]

    # Count by evidence source
    evidence_counts: dict[str, int] = {}
    for test in tests.test_cases:
        source = test.evidence_source
        evidence_counts[source] = evidence_counts.get(source, 0) + 1

    for source, count in sorted(evidence_counts.items()):
        lines.append(f"  - {source}: {count} test(s)")

    # Warnings
    if tests.warnings:
        lines.append("")
        lines.append("Warnings/Notes:")
        for warning in tests.warnings:
            lines.append(f"  - {warning}")

    # Saved path
    if meta.saved_to:
        lines.append(f"\nTests saved to: {meta.saved_to}")

    # Generated code
    lines.extend([
        "",
        "=" * 60,
        "GENERATED TEST CODE:",
        "=" * 60,
        "",
        tests.to_code()
    ])

    return "\n".join(lines)


# =============================================================================
# Helpers
# =============================================================================

def _error_response(result: ServiceResult) -> list[TextContent]:
    """Create error response from failed ServiceResult."""
    return [TextContent(type="text", text=f"Error: {result.error.message}")]
