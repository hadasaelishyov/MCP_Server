"""
Pytest Generator MCP Server

A Model Context Protocol server that generates pytest tests
using static code analysis (no AI required).
"""

import asyncio
import json
import logging
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .core import analyze_code
from .generators import generate_tests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
server = Server("pytest-generator")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="analyze_code",
            description="Analyze Python code structure. Validates syntax, extracts functions, "
                        "classes, methods, and calculates complexity. Returns warnings for "
                        "missing type hints and high complexity.",
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
            description="Generate pytest test cases for Python code. "
                        "Uses template-based generation with evidence-based enrichment: "
                        "doctest extraction, type assertions, exception detection, "
                        "boundary values, and naming heuristics. "
                        "Optionally uses AI to enhance assertions with real expected values.",
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
                        "description": "Whether to use AI to enhance tests with real expected values (default: false)"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "OpenAI API key (optional, uses OPENAI_API_KEY env var if not provided)"
                    }
                }
            }
        ),
        Tool(
            name="calculate_coverage",
            description="Estimate potential test coverage for Python code. "
                        "Returns coverage metrics and improvement suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Python file to analyze coverage for"
                    },
                    "code": {
                        "type": "string",
                        "description": "Python code content (alternative to file_path)"
                    }
                }
            }
        ),
    ]


def _get_code(arguments: dict) -> tuple[str | None, str | None]:
    """
    Get code from arguments (either file_path or code).
    
    Priority: file_path first, fallback to code if file fails.
    
    Returns:
        Tuple of (code, error_message)
    """
    file_path = arguments.get("file_path")
    code = arguments.get("code")
    
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read(), None
        except FileNotFoundError:
            if code:
                return code, None
            return None, f"File not found: {file_path}"
        except PermissionError:
            if code:
                return code, None
            return None, f"Permission denied: {file_path}"
        except Exception as e:
            if code:
                return code, None
            return None, f"Error reading file: {str(e)}"
    elif code:
        return code, None
    else:
        return None, "Please provide either 'file_path' or 'code'"


def _get_module_name(file_path: str | None) -> str:
    """Extract module name from file path."""
    if not file_path:
        return "module"
    
    # Get filename without extension
    basename = os.path.basename(file_path)
    name = os.path.splitext(basename)[0]
    return name


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    if name == "analyze_code":
        return await handle_analyze_code(arguments)
    
    elif name == "generate_tests":
        return await handle_generate_tests(arguments)
    
    elif name == "calculate_coverage":
        return [TextContent(
            type="text",
            text="🚧 calculate_coverage - Not yet implemented"
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def handle_analyze_code(arguments: dict) -> list[TextContent]:
    """Handle the analyze_code tool."""
    
    # Get code from file_path or code argument
    code, error = _get_code(arguments)
    
    if error:
        return [TextContent(
            type="text",
            text=f"Error: {error}"
        )]
    
    # Analyze the code
    result = analyze_code(code)
    
    # Format response
    if not result.valid:
        return [TextContent(
            type="text",
            text=f"Invalid code: {result.error}"
        )]
    
    # Build response
    response = {
        "valid": result.valid,
        "statistics": {
            "total_functions": result.total_functions,
            "total_classes": result.total_classes,
            "average_complexity": result.average_complexity,
            "type_hint_coverage": f"{result.type_hint_coverage}%"
        },
        "functions": [
            {
                "name": f.name,
                "parameters": [p.name for p in f.parameters],
                "return_type": f.return_type,
                "complexity": f.complexity,
                "has_docstring": f.docstring is not None
            }
            for f in result.functions
        ],
        "classes": [
            {
                "name": c.name,
                "methods": [m.name for m in c.methods]
            }
            for c in result.classes
        ],
        "warnings": result.warnings
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(response, indent=2)
    )]


async def handle_generate_tests(arguments: dict) -> list[TextContent]:
    """Handle the generate_tests tool."""
    from .generators import generate_tests, generate_tests_with_ai
    
    # Get code from file_path or code argument
    code, error = _get_code(arguments)
    
    if error:
        return [TextContent(
            type="text",
            text=f"Error: {error}"
        )]
    
    # Get options
    file_path = arguments.get("file_path")
    output_path = arguments.get("output_path")
    include_edge_cases = arguments.get("include_edge_cases", True)
    use_ai = arguments.get("use_ai", False)
    api_key = arguments.get("api_key")
    
    # Get module name
    module_name = _get_module_name(file_path)
    
    # Analyze the code first
    analysis = analyze_code(code)
    
    if not analysis.valid:
        return [TextContent(
            type="text",
            text=f"Cannot generate tests: {analysis.error}"
        )]
    
    # Generate tests (with or without AI)
    if use_ai:
        result = generate_tests_with_ai(
            analysis=analysis,
            source_code=code,
            module_name=module_name,
            include_edge_cases=include_edge_cases,
            api_key=api_key
        )
        mode = "AI-enhanced"
    else:
        result = generate_tests(
            analysis=analysis,
            source_code=code,
            module_name=module_name,
            include_edge_cases=include_edge_cases
        )
        mode = "Template"
    
    # Get the generated code
    test_code = result.to_code()
    
    # Save to file if output_path provided
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            save_message = f"\n\nTests saved to: {output_path}"
        except Exception as e:
            save_message = f"\n\nCould not save to file: {str(e)}"
    else:
        save_message = ""
    
    # Build response
    response_parts = [
        f"Generated {len(result.test_cases)} test(s) for {len(analysis.functions)} function(s) and {len(analysis.classes)} class(es)",
        f"Mode: {mode}",
        "",
        "Test breakdown by evidence source:",
    ]
    
    # Count by evidence source
    evidence_counts = {}
    for test in result.test_cases:
        source = test.evidence_source
        evidence_counts[source] = evidence_counts.get(source, 0) + 1
    
    for source, count in sorted(evidence_counts.items()):
        response_parts.append(f"  • {source}: {count} test(s)")
    
    if result.warnings:
        response_parts.append("")
        response_parts.append("Warnings/Notes:")
        for warning in result.warnings:
            response_parts.append(f"  • {warning}")
    
    response_parts.append("")
    response_parts.append("=" * 60)
    response_parts.append("GENERATED TEST CODE:")
    response_parts.append("=" * 60)
    response_parts.append("")
    response_parts.append(test_code)
    response_parts.append(save_message)
    
    return [TextContent(
        type="text",
        text="\n".join(response_parts)
    )]


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