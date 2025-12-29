"""
Analyze Code Tool - Analyze Python code structure.

This tool:
1. Validates Python syntax
2. Extracts functions, classes, methods, parameters
3. Calculates cyclomatic complexity
4. Reports type hint coverage
5. Warns about missing docstrings and high complexity

Uses AnalysisService for business logic.
"""

from __future__ import annotations

import json

from mcp.types import Tool, TextContent

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
    """
    Handle analyze_code tool call.
    
    Args:
        arguments: Tool arguments (file_path or code)
        
    Returns:
        List with single TextContent containing analysis results as JSON
    """
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
