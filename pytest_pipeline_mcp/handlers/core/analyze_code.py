"""MCP handler for the analyze_code tool (delegates to AnalysisService)."""

from __future__ import annotations

import json

from mcp.types import TextContent, Tool

from ...services import AnalysisService, ServiceResult

# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
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
)


# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """Analyze code from 'code' or 'file_path' and return JSON results."""
    service = AnalysisService()

    result = service.analyze(
        code=arguments.get("code"),
        file_path=arguments.get("file_path")
    )

    if not result.success:
        return _error_response(result)

    # Format as JSON
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


# =============================================================================
# Helpers
# =============================================================================

def _error_response(result: ServiceResult) -> list[TextContent]:
    """Create error response from failed ServiceResult."""
    return [TextContent(type="text", text=f"Error: {result.error.message}")]
