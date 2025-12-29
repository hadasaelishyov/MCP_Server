"""
Pytest Generator MCP Server

A Model Context Protocol server that generates pytest tests
using static code analysis and AI enhancement.

Architecture:
------------
This module is now THIN. It only handles:
1. MCP protocol (Tool definitions, TextContent responses)
2. Argument parsing (dict → service method args)
3. Response formatting (service results → text)

All business logic lives in the services layer.
"""

from __future__ import annotations

import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Services (all business logic)
from .services import (
    AnalysisService,
    GenerationService,
    ExecutionService,
    FixingService,
    ServiceResult,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
server = Server("pytest-generator")


# =============================================================================
# Tool Definitions
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="analyze_code",
            description=(
                "Analyze Python code structure. Validates syntax, extracts functions, "
                "classes, methods, and calculates complexity. Returns warnings for "
                "missing type hints and high complexity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Python file to analyze"
                    },
                    "code": {
                        "type": "string",
                        "description": "Python code content (alternative to file_path)"
                    }
                }
            }
        ),
        Tool(
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
                    },
                    "api_key": {
                        "type": "string",
                        "description": "OpenAI API key (optional, uses env var if not provided)"
                    }
                }
            }
        ),
        Tool(
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
        ),
        Tool(
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
                    },
                    "api_key": {
                        "type": "string",
                        "description": "OpenAI API key (optional, uses env var if not provided)"
                    }
                },
                "required": ["source_code", "test_code"]
            }
        ),
    ]


# =============================================================================
# Tool Router
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to handlers."""
    logger.info(f"Tool called: {name}")
    
    handlers = {
        "analyze_code": handle_analyze,
        "generate_tests": handle_generate,
        "run_tests": handle_run,
        "fix_code": handle_fix,
    }
    
    handler = handlers.get(name)
    if handler:
        return await handler(arguments)
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# Handlers (THIN - parse → call service → format)
# =============================================================================

async def handle_analyze(arguments: dict) -> list[TextContent]:
    """Handle analyze_code tool."""
    service = AnalysisService()
    
    result = service.analyze(
        code=arguments.get("code"),
        file_path=arguments.get("file_path")
    )
    
    if not result.success:
        return _error_response(result)
    
    # Format as JSON (matches original behavior)
    analysis = result.data
    response = {
        "valid": analysis.valid,
        "statistics": {
            "total_functions": analysis.total_functions,
            "total_classes": analysis.total_classes,
            "average_complexity": analysis.average_complexity,
            "type_hint_coverage": f"{analysis.type_hint_coverage}%"
        },
        "functions": [
            {
                "name": f.name,
                "parameters": [p.name for p in f.parameters],
                "return_type": f.return_type,
                "complexity": f.complexity,
                "has_docstring": f.docstring is not None
            }
            for f in analysis.functions
        ],
        "classes": [
            {
                "name": c.name,
                "methods": [m.name for m in c.methods]
            }
            for c in analysis.classes
        ],
        "warnings": analysis.warnings
    }
    
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_generate(arguments: dict) -> list[TextContent]:
    """Handle generate_tests tool."""
    service = GenerationService()
    
    result = service.generate(
        code=arguments.get("code"),
        file_path=arguments.get("file_path"),
        output_path=arguments.get("output_path"),
        include_edge_cases=arguments.get("include_edge_cases", True),
        use_ai=arguments.get("use_ai", False),
        api_key=arguments.get("api_key")
    )
    
    if not result.success:
        return _error_response(result)
    
    gen_result = result.data
    tests = gen_result.tests
    meta = gen_result.metadata
    
    # Build response text
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
        lines.append(f"  • {source}: {count} test(s)")
    
    # Warnings
    if tests.warnings:
        lines.append("")
        lines.append("Warnings/Notes:")
        for warning in tests.warnings:
            lines.append(f"  • {warning}")
    
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
    
    return [TextContent(type="text", text="\n".join(lines))]


async def handle_run(arguments: dict) -> list[TextContent]:
    """Handle run_tests tool."""
    service = ExecutionService()
    
    result = service.run(
        source_code=arguments.get("source_code", ""),
        test_code=arguments.get("test_code", "")
    )
    
    if not result.success:
        return _error_response(result)
    
    run_result = result.data
    
    # Build response text
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
    
    return [TextContent(type="text", text="\n".join(lines))]


async def handle_fix(arguments: dict) -> list[TextContent]:
    """Handle fix_code tool."""
    service = FixingService()
    
    result = service.fix(
        source_code=arguments.get("source_code", ""),
        test_code=arguments.get("test_code", ""),
        test_output=arguments.get("test_output"),
        verify=arguments.get("verify", True),
        api_key=arguments.get("api_key")
    )
    
    if not result.success:
        return _error_response(result)
    
    fix_result = result.data
    
    # Build response text
    lines = [
        "🔧 CODE FIX RESULTS",
        "=" * 50,
        "",
    ]
    
    if not fix_result.success:
        lines.append(f"❌ Fix failed: {fix_result.error}")
        return [TextContent(type="text", text="\n".join(lines))]
    
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
    
    return [TextContent(type="text", text="\n".join(lines))]


# =============================================================================
# Helpers
# =============================================================================

def _error_response(result: ServiceResult) -> list[TextContent]:
    """Create error response from failed ServiceResult."""
    error = result.error
    return [TextContent(type="text", text=f"Error: {error.message}")]


# =============================================================================
# Entry Point
# =============================================================================

async def run_server():
    """Run the MCP server."""
    logger.info("Starting Pytest Generator MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
